"""Latih + validasi lapisan ML PayRay.

    python -m engine --data data --out hasil
    python -m engine --data data_holdout --out hasil_holdout
    python -m ml --dev-data data --dev-hasil hasil --holdout-data data_holdout --holdout-hasil hasil_holdout

Desain (jujur terhadap kondisi lapangan):
- Label HANYA dari badan usaha yang diperiksa: 500 prioritas teratas + 250 audit acak (world dev).
- Bias seleksi dikoreksi dengan inverse propensity weighting (audit acak mewakili populasi sisanya).
- Validasi di world holdout: seed generator dan seed injeksi berbeda, tidak pernah dilihat saat training/tuning.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from . import model as M
from .quality import run_checks

K_INSPEKSI, N_AUDIT, TOP = 500, 250, 0.10
RP_COLS = ["estimasi_iuran_tak_tertagih", "est_upah", "est_headcount", "est_status"]


def load(data: Path, hasil: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    f = pd.read_csv(hasil / "fitur.csv", dtype={"kode_wilayah": str}).set_index("employer_id")
    r = pd.read_csv(hasil / "ranking.csv", dtype={"kode_wilayah": str}).set_index("employer_id").loc[f.index]
    lab = pd.read_csv(data / "label/labels.csv").set_index("employer_id").loc[f.index]
    return f, r, lab


def inspections(r: pd.DataFrame, seed: int = 0) -> tuple[pd.Index, pd.Series]:
    order = r.sort_values("prioritas", ascending=False).index
    top, rest = order[:K_INSPEKSI], order[K_INSPEKSI:]
    audit = pd.Index(np.random.default_rng(seed).choice(rest, size=N_AUDIT, replace=False))
    w = pd.concat([pd.Series(1.0, index=top), pd.Series(len(rest) / N_AUDIT, index=audit)])
    return top.append(audit), w


def topk(score: pd.Series, frac: float = TOP) -> pd.Index:
    return score.sort_values(ascending=False).index[: int(round(len(score) * frac))]


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True)


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> tuple[float, list[dict]]:
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, bins - 1)
    rows, e = [], 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            rows.append({"pred": float(p[m].mean()), "obs": float(y[m].mean()), "n": int(m.sum())})
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e), rows


def psi(a: pd.Series, b: pd.Series, bins: int = 10) -> float:
    a, b = a.dropna(), b.dropna()
    edges = np.unique(np.quantile(a, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    pa = np.histogram(np.clip(a, edges[0], edges[-1]), edges)[0] / len(a) + 1e-4
    pb = np.histogram(np.clip(b, edges[0], edges[-1]), edges)[0] / len(b) + 1e-4
    return float(np.sum((pa - pb) * np.log(pa / pb)))


def score_stats(score: pd.Series, lab: pd.DataFrame, f: pd.DataFrame) -> dict:
    y = lab.is_violator
    top = topk(score)
    umkm_ok = (y == 0) & f.skala_usaha.isin(["mikro", "kecil"])
    loss = lab.iuran_tak_tertagih_tahun_terakhir
    return {
        "roc_auc": float(roc_auc_score(y, score)), "pr_auc": float(average_precision_score(y, score)),
        "precision_top": float(y.loc[top].mean()), "recall_top": float(y.loc[top].sum() / y.sum()),
        "lift": float(y.loc[top].mean() / y.mean()),
        "salah_tandai_umkm": float(umkm_ok.loc[top].sum() / umkm_ok.sum()),
        "iuran_per100": float(loss.loc[score.sort_values(ascending=False).index[:100]].sum()),
        "recall_sulit": float((lab.loc[top].kesulitan == "sulit").sum() / max(1, (lab.kesulitan == "sulit").sum())),
    }


def bootstrap_ci(score: pd.Series, y: pd.Series, n: int = 1000, seed: int = 7) -> list[float]:
    rng = np.random.default_rng(seed)
    s, yy = score.to_numpy(), y.to_numpy()
    k = int(round(len(s) * TOP))
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(s), len(s))
        o = np.argsort(-s[i], kind="stable")[:k]
        vals.append(yy[i][o].mean())
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def prec_curve(score: pd.Series, y: pd.Series) -> list[float]:
    o = y.loc[score.sort_values(ascending=False).index].to_numpy()
    return [float(o[: int(round(len(o) * q / 100))].mean()) for q in range(1, 31)]


# ------------------------------------------------------------------------------------- Rp interval (CQR)

def rp_matrix(f: pd.DataFrame, r: pd.DataFrame) -> pd.DataFrame:
    X = M.matrix(f)
    for c in RP_COLS:
        X["log_" + c] = np.log1p(r[c].clip(lower=0))
    X["log_umk"] = np.log(f.umk_terakhir)
    return X


def fit_cqr(X: pd.DataFrame, y: pd.Series, alpha: float = 0.2, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X))
    cut = int(len(X) * 0.7)
    tr, ca = idx[:cut], idx[cut:]
    ly = np.log1p(y.to_numpy())
    ms = {}
    for q in (alpha / 2, 0.5, 1 - alpha / 2):
        ms[q] = HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=200, learning_rate=0.05,
                                              max_leaf_nodes=8, min_samples_leaf=10, random_state=seed)
        ms[q].fit(X.iloc[tr], ly[tr])
    lo, hi = ms[alpha / 2].predict(X.iloc[ca]), ms[1 - alpha / 2].predict(X.iloc[ca])
    E = np.maximum(lo - ly[ca], ly[ca] - hi)
    n = len(ca)
    qhat = float(np.quantile(E, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)))
    return {"m": ms, "qhat": qhat, "alpha": alpha, "n_train": len(tr), "n_cal": n}


def predict_cqr(c: dict, X: pd.DataFrame) -> pd.DataFrame:
    a = c["alpha"]
    lo = c["m"][a / 2].predict(X) - c["qhat"]
    md = c["m"][0.5].predict(X)
    hi = c["m"][1 - a / 2].predict(X) + c["qhat"]
    out = pd.DataFrame({"lo": np.expm1(lo), "med": np.expm1(md), "hi": np.expm1(hi)}, index=X.index)
    out["lo"] = out.lo.clip(lower=0)
    out["med"] = out[["med", "lo"]].max(axis=1).clip(upper=out.hi)
    return out


# ------------------------------------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-data", type=Path, default=Path("data"))
    ap.add_argument("--dev-hasil", type=Path, default=Path("hasil"))
    ap.add_argument("--holdout-data", type=Path, default=Path("data_holdout"))
    ap.add_argument("--holdout-hasil", type=Path, default=Path("hasil_holdout"))
    ap.add_argument("--artefak", type=Path, default=Path("ml/artefak"))
    a = ap.parse_args()
    a.artefak.mkdir(parents=True, exist_ok=True)

    f, r, lab = load(a.dev_data, a.dev_hasil)
    fh, rh, labh = load(a.holdout_data, a.holdout_hasil)
    X, Xh = M.matrix(f), M.matrix(fh)
    insp, w = inspections(r)
    y = lab.is_violator
    grp = pd.Series(np.where(insp.isin(insp[:K_INSPEKSI]), 0, 1), index=insp)
    print(f"label dari pemeriksaan: {len(insp)} badan usaha ({int(y.loc[insp].sum())} terbukti)")

    # OOF (out-of-fold) di data pemeriksaan -> kalibrasi isotonic berbobot IPW
    oof = pd.Series(np.nan, index=insp)
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    strat = grp.astype(str) + "_" + y.loc[insp].astype(str)
    for tr, te in skf.split(insp, strat):
        m = M.fit(X.loc[insp[tr]], y.loc[insp[tr]], w.loc[insp[tr]])
        oof.iloc[te] = m.predict_proba(X.loc[insp[te]])[:, 1]
    iso = M.calibrator(oof.to_numpy(), y.loc[insp].to_numpy(), w.loc[insp].to_numpy())
    clf = M.fit(X.loc[insp], y.loc[insp], w.loc[insp])
    js = M.export(clf, iso, X)

    # uji kesamaan evaluator ekspor (dipakai browser) vs sklearn
    raw_sk = clf._raw_predict(Xh.to_numpy())[:, 0]
    raw_js = np.array([M.contributions(js, x)[0] for x in Xh.to_numpy()[:300]])
    gap = float(np.abs(raw_sk[:300] - raw_js).max())
    assert gap < 1e-4, f"ekspor model tidak sama dengan sklearn (selisih {gap})"
    print(f"evaluator JSON == sklearn (selisih maks log-odds {gap:.1e}), {len(js['trees'])} pohon")

    def p_cal(m, XX):
        return pd.Series(np.interp(m.predict_proba(XX)[:, 1], js["kalibrasi"]["x"], js["kalibrasi"]["y"]), index=XX.index)

    p_dev = p_cal(clf, X)
    p_dev.loc[insp] = np.interp(oof, js["kalibrasi"]["x"], js["kalibrasi"]["y"])  # label tidak bocor ke skor
    p_h = p_cal(clf, Xh)

    # stacking: logit(ML mentah) + persentil prioritas aturan -> peluang gabungan terkalibrasi (fit di OOF, bobot IPW)
    def Z(raw: pd.Series, prio: pd.Series) -> np.ndarray:
        return np.column_stack([logit(raw.to_numpy()), pct_rank(prio).loc[raw.index].to_numpy()])

    raw_dev = pd.Series(clf.predict_proba(X)[:, 1], index=X.index)
    raw_dev.loc[insp] = oof
    raw_h = pd.Series(clf.predict_proba(Xh)[:, 1], index=Xh.index)
    stk = LogisticRegression(C=1.0).fit(Z(raw_dev.loc[insp], r.prioritas), y.loc[insp], sample_weight=w.loc[insp])
    js["stack"] = {"ml": float(stk.coef_[0, 0]), "aturan": float(stk.coef_[0, 1]), "c": float(stk.intercept_[0])}
    g_dev = pd.Series(stk.predict_proba(Z(raw_dev, r.prioritas))[:, 1], index=X.index)
    g_h = pd.Series(stk.predict_proba(Z(raw_h, rh.prioritas))[:, 1], index=Xh.index)

    # ------------------------------------------------------------------ interval Rp (CQR) dari pelanggar terbukti (dev)
    v = insp[y.loc[insp].to_numpy() == 1]
    R, Rh = rp_matrix(f, r), rp_matrix(fh, rh)
    cqr = fit_cqr(R.loc[v], lab.loc[v, "iuran_tak_tertagih_tahun_terakhir"])
    rp_h = predict_cqr(cqr, Rh).med

    # ------------------------------------------------------------------ validasi di world holdout
    yh = labh.is_violator
    scores = {
        "Acak": pd.Series(np.random.default_rng(3).random(len(yh)), index=yh.index),
        "Aturan + Isolation Forest": rh.prioritas,
        "Model ML (dari hasil pemeriksaan)": p_h,
        "PayRay gabungan (stacking)": g_h,
        "Gabungan × estimasi Rp (nilai harapan)": g_h * rp_h,
    }
    comp = {k: score_stats(s, labh, fh) for k, s in scores.items()}
    for k, s in scores.items():
        comp[k]["precision_ci95"] = bootstrap_ci(s, yh)
        comp[k]["kurva_precision"] = prec_curve(s, yh)
    e, rel = ece(g_h.to_numpy(), yh.to_numpy())
    e_ml, rel_ml = ece(p_h.to_numpy(), yh.to_numpy())
    kal = {"brier": float(brier_score_loss(yh, g_h)), "brier_ml": float(brier_score_loss(yh, p_h)),
           "brier_acak": float(yh.mean() * (1 - yh.mean())), "ece": e, "ece_ml": e_ml,
           "reliability": rel, "reliability_ml": rel_ml}

    # kesepakatan dua metode independen
    t_r, t_m = set(topk(rh.prioritas)), set(topk(p_h))
    quad = {}
    for nm, ids in {"Keduanya menandai": t_r & t_m, "Hanya aturan": t_r - t_m, "Hanya ML": t_m - t_r}.items():
        ids = list(ids)
        quad[nm] = {"n": len(ids), "precision": float(yh.loc[ids].mean()) if ids else None}

    # learning curve: berapa banyak hasil pemeriksaan yang dibutuhkan
    lc = []
    rng = np.random.default_rng(11)
    for frac in (0.2, 0.4, 0.6, 0.8, 1.0):
        aps, pts = [], []
        for rep in range(5 if frac < 1 else 1):
            sub = insp if frac == 1 else pd.Index(rng.choice(insp, int(len(insp) * frac), replace=False))
            m = M.fit(X.loc[sub], y.loc[sub], w.loc[sub], seed=rep)
            s = pd.Series(m.predict_proba(Xh)[:, 1], index=Xh.index)
            aps.append(average_precision_score(yh, s))
            pts.append(yh.loc[topk(s)].mean())
        lc.append({"n_label": int(len(insp) * frac), "pr_auc": float(np.mean(aps)), "pr_auc_sd": float(np.std(aps)),
                   "precision_top": float(np.mean(pts))})

    # stabilitas: bootstrap data training + seed berbeda
    base_top = set(topk(p_h))
    st = []
    for rep in range(10):
        sub = pd.Index(rng.choice(insp, len(insp), replace=True))
        m = M.fit(X.loc[sub], y.loc[sub], w.loc[sub], seed=100 + rep)
        s = pd.Series(m.predict_proba(Xh)[:, 1], index=Xh.index)
        tt = set(topk(s))
        st.append({"precision_top": float(yh.loc[list(tt)].mean()), "jaccard": len(tt & base_top) / len(tt | base_top)})
    stab = {"precision_mean": float(np.mean([s["precision_top"] for s in st])),
            "precision_sd": float(np.std([s["precision_top"] for s in st])),
            "jaccard_mean": float(np.mean([s["jaccard"] for s in st]))}

    # importance: permutation (holdout, PR-AUC) + rata-rata |kontribusi| (Saabas)
    pi = permutation_importance(clf, Xh, yh, scoring="average_precision", n_repeats=5, random_state=0)
    phi = np.array([M.contributions(js, x)[1] for x in Xh.to_numpy()])
    imp = sorted([{"fitur": M.LABELS[c], "kolom": c, "permutation": float(pi.importances_mean[i]),
                   "permutation_sd": float(pi.importances_std[i]), "kontribusi": float(np.abs(phi[:, i]).mean())}
                  for i, c in enumerate(M.COLS)], key=lambda d: -d["permutation"])

    # fairness per skala (gabungan)
    g = g_h
    top_g = set(topk(g))
    fair = []
    for sk in ["mikro", "kecil", "menengah", "besar"]:
        ids = fh.index[fh.skala_usaha == sk]
        flag = ids.isin(list(top_g))
        ok = (yh.loc[ids] == 0).to_numpy()
        fair.append({"skala": sk, "n": len(ids), "precision": float(yh.loc[ids[flag]].mean()) if flag.any() else None,
                     "recall": float((flag & ~ok).sum() / max(1, (~ok).sum())),
                     "salah_tandai": float((flag & ok).sum() / max(1, ok.sum()))})

    # drift dev -> holdout
    drift = sorted([{"fitur": M.LABELS[c], "psi": psi(X[c], Xh[c])} for c in M.COLS], key=lambda d: -d["psi"])

    flagged_v = [i for i in topk(g) if yh.loc[i] == 1]
    ph_int = predict_cqr(cqr, Rh.loc[flagged_v])
    true = labh.loc[flagged_v, "iuran_tak_tertagih_tahun_terakhir"]
    calc = rh.loc[flagged_v, "estimasi_iuran_tak_tertagih"]
    rp_val = {
        "target_coverage": 1 - cqr["alpha"], "n_train": cqr["n_train"], "n_kalibrasi": cqr["n_cal"],
        "coverage_holdout": float(((true >= ph_int.lo) & (true <= ph_int.hi)).mean()),
        "n_holdout": len(flagged_v),
        "lebar_median_rasio": float(((ph_int.hi - ph_int.lo) / ph_int.med.clip(lower=1)).median()),
        "korelasi_log_kalkulator": float(np.corrcoef(np.log1p(calc), np.log1p(true))[0, 1]),
        "korelasi_log_ml": float(np.corrcoef(np.log1p(ph_int.med), np.log1p(true))[0, 1]),
        "mape_median_kalkulator": float((np.abs(calc - true) / true).median()),
        "mape_median_ml": float((np.abs(ph_int.med - true) / true).median()),
    }
    dev_int = predict_cqr(cqr, R)

    # ------------------------------------------------------------------ kualitas data input
    dq = run_checks(a.dev_data)

    val = {
        "desain": {"label_dari_pemeriksaan": len(insp), "top_prioritas": K_INSPEKSI, "audit_acak": N_AUDIT,
                   "terbukti": int(y.loc[insp].sum()), "bobot_audit_ipw": float(w.iloc[-1]),
                   "holdout_n": len(yh), "holdout_prevalensi": float(yh.mean()), "pohon": len(js["trees"]),
                   "fitur": len(M.COLS), "selisih_ekspor": gap},
        "perbandingan": comp, "kalibrasi": kal, "kesepakatan": quad, "learning_curve": lc,
        "stabilitas": stab, "importance": imp, "fairness": fair, "drift": drift, "rupiah": rp_val,
        "kualitas_data": dq,
    }
    (a.artefak / "model_payray.json").write_text(json.dumps(js, separators=(",", ":")), encoding="utf-8")
    (a.artefak / "validasi.json").write_text(json.dumps(val, ensure_ascii=False, indent=1), encoding="utf-8")
    pred = pd.DataFrame({"p_ml": p_dev.round(4), "p_gabungan": g_dev.round(4),
                         "persentil_aturan": pct_rank(r.prioritas).round(5), "diperiksa": f.index.isin(insp).astype(int),
                         "rp_lo": dev_int.lo.round(-3), "rp_med": dev_int.med.round(-3), "rp_hi": dev_int.hi.round(-3)})
    pred.index.name = "employer_id"
    pred.to_csv(a.dev_hasil / "ml_prediksi.csv")
    (a.artefak / "laporan_ml.md").write_text(report(val), encoding="utf-8")

    for k, c in comp.items():
        print(f"{k:36s} P@10% {c['precision_top']:.1%} [{c['precision_ci95'][0]:.1%}–{c['precision_ci95'][1]:.1%}]"
              f"  PR-AUC {c['pr_auc']:.3f}  ROC {c['roc_auc']:.3f}  UMKM {c['salah_tandai_umkm']:.1%}"
              f"  Rp/100 {c['iuran_per100'] / 1e9:.2f} M  sulit {c['recall_sulit']:.0%}")
    print("kalibrasi:", {k: round(v, 4) for k, v in kal.items() if not k.startswith("reliability")})
    print("kesepakatan:", quad)
    print("stabilitas:", stab)
    print("rupiah:", {k: round(v, 3) if isinstance(v, float) else v for k, v in rp_val.items()})
    print("kualitas data:", sum(c["status"] == "lulus" for c in dq), "/", len(dq), "lulus")


def report(v: dict) -> str:
    d, c = v["desain"], v["perbandingan"]
    L = ["# Laporan Validasi Model ML PayRay", "",
         f"Training: {d['label_dari_pemeriksaan']} hasil pemeriksaan di world dev ({d['top_prioritas']} prioritas teratas + "
         f"{d['audit_acak']} audit acak, bobot IPW audit {d['bobot_audit_ipw']:.1f}). "
         f"Test: world holdout {d['holdout_n']:,} badan usaha (prevalensi {d['holdout_prevalensi']:.1%}), "
         "seed generator dan seed injeksi berbeda, tidak pernah dilihat saat training/tuning.", "",
         "## Perbandingan metode (holdout, top-10%)", "",
         "| Metode | Precision@10% (CI 95%) | PR-AUC | ROC-AUC | Recall kasus sulit | Salah tandai UMKM | Iuran/100 pemeriksaan |",
         "|---|---|---|---|---|---|---|"]
    for k, s in c.items():
        lo, hi = s["precision_ci95"]
        L.append(f"| {k} | {s['precision_top']:.1%} ({lo:.1%}–{hi:.1%}) | {s['pr_auc']:.3f} | {s['roc_auc']:.3f} | "
                 f"{s['recall_sulit']:.0%} | {s['salah_tandai_umkm']:.1%} | Rp{s['iuran_per100'] / 1e9:.2f} M |")
    k = v["kalibrasi"]
    L += ["", "## Kalibrasi probabilitas", "",
          f"Gabungan: Brier {k['brier']:.4f} · ECE {k['ece']:.3f}. Model ML saja: Brier {k['brier_ml']:.4f} · ECE {k['ece_ml']:.3f}. "
          f"Baseline (prevalensi saja): Brier {k['brier_acak']:.4f}.", "",
          "## Kesepakatan dua metode independen", "", "| Kelompok | n | Precision |", "|---|---|---|"]
    L += [f"| {n} | {q['n']} | {q['precision']:.1%} |" for n, q in v["kesepakatan"].items() if q["precision"] is not None]
    s = v["stabilitas"]
    L += ["", "## Stabilitas & learning curve", "",
          f"10× bootstrap training: precision {s['precision_mean']:.1%} ± {s['precision_sd']:.1%}, "
          f"overlap top-10% (Jaccard) {s['jaccard_mean']:.2f}", "", "| Label pemeriksaan | PR-AUC | Precision@10% |", "|---|---|---|"]
    L += [f"| {x['n_label']} | {x['pr_auc']:.3f} ± {x['pr_auc_sd']:.3f} | {x['precision_top']:.1%} |" for x in v["learning_curve"]]
    L += ["", "## Permutation importance (holdout, penurunan PR-AUC)", "", "| Fitur | Δ PR-AUC |", "|---|---|"]
    L += [f"| {x['fitur']} | {x['permutation']:.3f} ± {x['permutation_sd']:.3f} |" for x in v["importance"][:10]]
    rp = v["rupiah"]
    L += ["", "## Rentang estimasi Rp (conformalized quantile regression)", "",
          f"Target coverage {rp['target_coverage']:.0%} → coverage holdout **{rp['coverage_holdout']:.1%}** "
          f"(n = {rp['n_holdout']} pelanggar yang tertangkap). Korelasi log: kalkulator {rp['korelasi_log_kalkulator']:.2f} → "
          f"model {rp['korelasi_log_ml']:.2f}. Median galat relatif: kalkulator {rp['mape_median_kalkulator']:.0%} → "
          f"model {rp['mape_median_ml']:.0%}.", "",
          "## Fairness per skala (gabungan)", "", "| Skala | n | Precision | Recall | Salah tandai patuh |", "|---|---|---|---|---|"]
    L += [f"| {x['skala']} | {x['n']} | {(x['precision'] or 0):.0%} | {x['recall']:.0%} | {x['salah_tandai']:.1%} |" for x in v["fairness"]]
    L += ["", "## Drift fitur dev → holdout (PSI)", "", "| Fitur | PSI |", "|---|---|"]
    L += [f"| {x['fitur']} | {x['psi']:.3f} |" for x in v["drift"][:6]]
    L += ["", "## Kualitas data input", "", "| Pemeriksaan | Status | Temuan |", "|---|---|---|"]
    L += [f"| {x['nama']} | {x['status']} | {x['temuan']} |" for x in v["kualitas_data"]]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
