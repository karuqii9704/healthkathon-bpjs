"""Evaluasi mesin scan terhadap label (HANYA evaluator yang punya data/label/)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def evaluate(res: pd.DataFrame, data: Path, top_frac: float = 0.10) -> dict:
    lab = pd.read_csv(data / "label/labels.csv").set_index("employer_id").loc[res.index]
    order = res.sort_values("prioritas", ascending=False).index
    k = int(round(len(order) * top_frac))
    top = lab.loc[order[:k]]
    prev = lab.is_violator.mean()
    umkm_ok = (lab.is_violator == 0) & res.skala_usaha.isin(["mikro", "kecil"])

    loss = lab.iuran_tak_tertagih_tahun_terakhir
    top100 = loss.loc[order[:100]].sum()
    acak100 = loss.mean() * 100

    v = lab.is_violator == 1
    est, true = res.estimasi_iuran_tak_tertagih[v], loss[v]
    hit = top.index[top.is_violator == 1]

    m = {
        "n": len(lab), "prevalensi": prev,
        "precision_top": top.is_violator.mean(),
        "lift": top.is_violator.mean() / prev,
        "recall_top": top.is_violator.sum() / lab.is_violator.sum(),
        "recall_mudah": (top.kesulitan == "mudah").sum() / max(1, (lab.kesulitan == "mudah").sum()),
        "recall_sulit": (top.kesulitan == "sulit").sum() / max(1, (lab.kesulitan == "sulit").sum()),
        "hard_negative_di_top": int((top.kesulitan == "hard_negative").sum()),
        "salah_tandai_umkm": umkm_ok.loc[order[:k]].sum() / max(1, umkm_ok.sum()),
        "iuran_top100": top100, "iuran_acak100": acak100,
        "hit_top100": lab.is_violator.loc[order[:100]].mean(),
        "korelasi_estimasi": float(np.corrcoef(np.log1p(est), np.log1p(true))[0, 1]),
        "rasio_estimasi_median": float((res.estimasi_iuran_tak_tertagih[hit] / loss[hit]).median()),
    }
    # per skala usaha (uji bias)
    rows = []
    for sk in ["mikro", "kecil", "menengah", "besar"]:
        idx = res.index[res.skala_usaha == sk]
        intop = pd.Series(idx.isin(order[:k]), index=idx)
        ok = lab.loc[idx, "is_violator"] == 0
        rows.append({
            "skala": sk, "n": len(idx), "pelanggar": int((~ok).sum()),
            "ditandai": int(intop.sum()),
            "precision": lab.loc[idx[intop.to_numpy()], "is_violator"].mean() if intop.any() else np.nan,
            "recall": (intop & ~ok).sum() / max(1, (~ok).sum()),
            "salah_tandai": (intop & ok).sum() / max(1, ok.sum()),
        })
    m["per_skala"] = pd.DataFrame(rows)
    # per modus
    rows = []
    for mod in ["lapor_umk", "upah_beku", "potong_sebagian", "daftar_sebagian", "pindah_pbpu"]:
        ids = lab.index[lab.modus.fillna("").str.contains(mod)]
        rows.append({"modus": mod, "n": len(ids), "recall": pd.Index(ids).isin(order[:k]).mean()})
    m["per_modus"] = pd.DataFrame(rows)
    return m


def report(m: dict) -> str:
    L = ["# Laporan Akurasi Mesin Scan PayRay", "",
         "Data simulasi (generator PayRay). Mesin hanya membaca `publik/` + `referensi/`; label dipakai di sini saja.", "",
         "## Metrik utama (top-10% prioritas)", "",
         "| Metrik | Target CLAUDE.md | Hasil |", "|---|---|---|",
         f"| Precision@top-10% | ≥ 70% | **{m['precision_top']:.1%}** |",
         f"| Lift vs acak (prevalensi {m['prevalensi']:.0%}) | ≈ 4,7× | **{m['lift']:.2f}×** |",
         f"| Salah tandai UMKM patuh | ≤ 5% | **{m['salah_tandai_umkm']:.1%}** |",
         f"| Iuran tertangkap per 100 pemeriksaan (tahun terakhir) | > acak | **Rp{m['iuran_top100']:,.0f}** vs acak Rp{m['iuran_acak100']:,.0f} ({m['iuran_top100'] / m['iuran_acak100']:.1f}×) |",
         "", f"- Recall top-10%: {m['recall_top']:.1%} (mudah {m['recall_mudah']:.1%} · sulit {m['recall_sulit']:.1%})",
         f"- Hard negative ikut masuk top-10%: {m['hard_negative_di_top']}",
         f"- Hit rate 100 teratas: {m['hit_top100']:.0%}",
         f"- Kalkulator estimasi vs kerugian sebenarnya: korelasi log {m['korelasi_estimasi']:.2f}, "
         f"rasio median estimasi/sebenarnya pada pelanggar yang tertangkap {m['rasio_estimasi_median']:.2f}", "",
         "## Uji bias per skala usaha", "",
         "| Skala | Badan usaha | Pelanggar | Ditandai | Precision | Recall | Salah tandai patuh |", "|---|---|---|---|---|---|---|"]
    for r in m["per_skala"].itertuples():
        L.append(f"| {r.skala} | {r.n} | {r.pelanggar} | {r.ditandai} | {r.precision:.0%} | {r.recall:.0%} | {r.salah_tandai:.1%} |")
    L += ["", "## Recall per modus", "", "| Modus | Jumlah | Recall top-10% |", "|---|---|---|"]
    L += [f"| {r.modus} | {r.n} | {r.recall:.0%} |" for r in m["per_modus"].itertuples()]
    return "\n".join(L) + "\n"
