"""Validasi dataset sintetis: invarian, tingkat kesulitan, dan kebocoran label.

Jalankan terpisah: python -m generator.validate data/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .calculator import iuran_ppu


def _load(out: Path) -> dict[str, pd.DataFrame]:
    files = {
        "emp": "publik/employers.csv", "workers": "publik/workers.csv", "wages": "publik/wage_history.csv",
        "mut": "publik/mutations.csv", "umk": "referensi/umk.csv", "labels": "label/labels.csv",
        "hidden": "label/hidden_workers.csv", "truth": "label/upah_riil.csv",
    }
    d = {k: pd.read_csv(out / v, dtype={"kbli": str, "kode_wilayah": str}, low_memory=False) for k, v in files.items()}
    for k in ("workers", "mut", "hidden"):
        for c in ("tgl_masuk", "tgl_keluar", "tanggal", "tgl_segmen_baru"):
            if c in d[k]:
                d[k][c] = pd.to_datetime(d[k][c])
    return d


def baseline_features(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Fitur naif per badan usaha — cikal bakal Scan Upah/Headcount/Status."""
    emp, wages, umk, mut = d["emp"], d["wages"], d["umk"], d["mut"]
    w = wages.merge(emp[["employer_id", "kode_wilayah"]], on="employer_id").merge(umk[["kode_wilayah", "tahun", "umk"]])
    last = w.groupby("employer_id").tahun.transform("max")
    wl = w[w.tahun == last]
    f = pd.DataFrame(index=emp.employer_id)
    f["porsi_tepat_umk"] = (wl.upah_dilaporkan == wl.umk).groupby(wl.employer_id).mean()
    f["porsi_bawah_umk"] = (wl.upah_dilaporkan < wl.umk).groupby(wl.employer_id).mean()
    hc = wl.groupby("employer_id").worker_id.nunique()
    f["rasio_headcount_oss"] = hc / emp.set_index("employer_id").tk_oss
    pb = mut[(mut.jenis == "KELUAR_PPU") & (mut.segmen_tujuan == "PBPU")
             & ((mut.tgl_segmen_baru - mut.tanggal).dt.days <= 30)]
    cl = pb.groupby([pb.employer_id, pb.tanggal.dt.to_period("M")]).size().groupby(level=0).max()
    f["klaster_pbpu"] = cl / w.groupby("employer_id").worker_id.nunique()
    return f.fillna({"porsi_tepat_umk": 0, "porsi_bawah_umk": 0, "klaster_pbpu": 0, "rasio_headcount_oss": 1})


def _topk_report(score: pd.Series, lab: pd.DataFrame, emp: pd.DataFrame) -> dict:
    k = int(round(len(score) * 0.10))
    top = score.sort_values(ascending=False).index[:k]
    L = lab.set_index("employer_id")
    t = L.loc[top]
    umkm_patuh = L.index[(L.is_violator == 0) & emp.set_index("employer_id").skala_usaha.isin(["mikro", "kecil"]).reindex(L.index)]
    prev = L.is_violator.mean()
    prec = t.is_violator.mean()
    return {
        "precision@10%": prec,
        "lift": prec / prev,
        "recall mudah": (t.kesulitan == "mudah").sum() / max(1, (L.kesulitan == "mudah").sum()),
        "recall sulit": (t.kesulitan == "sulit").sum() / max(1, (L.kesulitan == "sulit").sum()),
        "hard neg di top": int((t.kesulitan == "hard_negative").sum()),
        "salah tandai UMKM": np.isin(top, umkm_patuh).sum() / max(1, len(umkm_patuh)),
    }


def validate(out: Path) -> tuple[str, bool]:
    d = _load(out)
    emp, workers, wages, lab, truth = d["emp"], d["workers"], d["wages"], d["labels"], d["truth"]
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # --- invarian ---
    check("worker_id unik", workers.worker_id.is_unique)
    check("pekerja tersembunyi tidak muncul di data publik", not d["hidden"].worker_id.isin(workers.worker_id).any())
    check("riwayat upah merujuk pekerja terdaftar", wages.worker_id.isin(workers.worker_id).all())
    j = wages.merge(truth, on=["worker_id", "tahun"], suffixes=("", "_riil"))
    check("upah dilaporkan <= upah riil", (j.upah_dilaporkan <= j.upah_riil).all())
    check("bulan_aktif 1..12", wages.bulan_aktif.between(1, 12).all())
    check("tgl_keluar >= tgl_masuk", (workers.tgl_keluar.isna() | (workers.tgl_keluar >= workers.tgl_masuk)).all())
    ok_lab = lab[lab.is_violator == 0]
    check("patuh: iuran tak tertagih = 0", (ok_lab.iuran_tak_tertagih_total == 0).all())
    bad = lab[lab.is_violator == 1]
    check("pelanggar: iuran tak tertagih > 0", (bad.iuran_tak_tertagih_total > 0).all(),
          f"{(bad.iuran_tak_tertagih_total <= 0).sum()} pelanggar tanpa kerugian")
    check("kolom label tidak bocor ke employers.csv",
          not set(emp.columns) & {"is_violator", "modus", "kesulitan", "hard_negative_type"})
    big = emp.loc[emp.skala_usaha.isin(["menengah", "besar"]), "employer_id"]
    tw = truth[truth.employer_id.isin(big)].merge(emp[["employer_id", "kode_wilayah"]]).merge(d["umk"][["kode_wilayah", "tahun", "umk"]])
    check("upah riil menengah/besar >= UMK", (tw.upah_riil >= tw.umk).all())

    # --- kebocoran label dari metadata badan usaha ---
    m = emp.merge(lab[["employer_id", "is_violator"]])
    leak = []
    for c in ("tk_oss", "tahun_berdiri"):
        auc = roc_auc_score(m.is_violator, m[c])
        leak.append((c, f"AUC {auc:.3f}", abs(auc - 0.5) < 0.08))
    for c in ("skala_usaha", "kbli", "kode_wilayah"):
        r = m.groupby(c).is_violator.agg(["mean", "size"])
        r = r[r["size"] >= 50]
        if len(r) < 2:
            leak.append((c, "sampel per kategori terlalu kecil", True))
            continue
        spread = r["mean"].max() - r["mean"].min()
        leak.append((c, f"rentang prevalensi {spread:.1%} ({len(r)} kategori n≥50)", spread < 0.12))

    # --- tingkat kesulitan: aturan naif tidak boleh langsung sempurna ---
    f = baseline_features(d)
    rules = {
        "porsi tepat UMK": f.porsi_tepat_umk,
        "porsi di bawah UMK": f.porsi_bawah_umk,
        "headcount vs OSS (rendah)": -f.rasio_headcount_oss,
        "klaster pindah PBPU": f.klaster_pbpu,
        "gabungan rank naif": f.rank(pct=True).assign(rasio_headcount_oss=1 - f.rasio_headcount_oss.rank(pct=True)).mean(axis=1),
    }
    base = {name: _topk_report(s, lab, emp) for name, s in rules.items()}
    too_easy = base["gabungan rank naif"]["precision@10%"] >= 0.9

    # --- laporan ---
    L = []
    L.append("# Laporan Validasi Data Sintetis PayRay\n")
    L.append(f"- Badan usaha: **{len(emp):,}** · pekerja terdaftar: **{len(workers):,}** · baris upah: **{len(wages):,}**")
    L.append(f"- Pelanggar: **{lab.is_violator.sum():,}** ({lab.is_violator.mean():.1%})  "
             f"· mudah {(lab.kesulitan == 'mudah').sum()} · sulit {(lab.kesulitan == 'sulit').sum()}")
    L.append(f"- Hard negative (patuh tapi tampak mencurigakan): **{(lab.kesulitan == 'hard_negative').sum()}**")
    hn = lab[lab.kesulitan == "hard_negative"].hard_negative_type.value_counts()
    L.append("  - " + " · ".join(f"{k}: {v}" for k, v in hn.items()))
    modus = bad.modus.str.split("|").explode().value_counts()
    L.append("- Modus: " + " · ".join(f"{k}: {v}" for k, v in modus.items()))
    tot = bad.iuran_tak_tertagih_tahun_terakhir.sum()
    L.append(f"- Iuran tak tertagih (tahun terakhir, kebenaran): **Rp{tot:,.0f}** "
             f"· median per pelanggar Rp{bad.iuran_tak_tertagih_tahun_terakhir.median():,.0f}\n")

    L.append("## Invarian\n")
    L.append("| Cek | Hasil | Catatan |\n|---|---|---|")
    L += [f"| {n} | {'✅' if ok else '❌'} | {det} |" for n, ok, det in checks]

    L.append("\n## Kebocoran label dari metadata\n")
    L.append("Metadata badan usaha seharusnya tidak memprediksi label (AUC ≈ 0,5; prevalensi rata).\n")
    L.append("| Kolom | Statistik | Aman |\n|---|---|---|")
    L += [f"| {c} | {s} | {'✅' if ok else '⚠️'} |" for c, s, ok in leak]

    L.append("\n## Baseline aturan naif (top-10%)\n")
    L.append("Patokan yang harus dikalahkan model. Kalau aturan naif sudah ≥ 90% precision, data terlalu mudah.\n")
    L.append("| Aturan | Precision | Lift | Recall mudah | Recall sulit | Hard neg di top | Salah tandai UMKM |")
    L.append("|---|---|---|---|---|---|---|")
    for name, r in base.items():
        L.append(f"| {name} | {r['precision@10%']:.1%} | {r['lift']:.2f}× | {r['recall mudah']:.1%} | "
                 f"{r['recall sulit']:.1%} | {r['hard neg di top']} | {r['salah tandai UMKM']:.1%} |")
    if too_easy:
        L.append("\n⚠️ Aturan naif gabungan sudah ≥ 90% precision — naikkan porsi kasus sulit / hard negative.")

    ok_all = all(ok for _, ok, _ in checks)
    L.append(f"\n**Status: {'LULUS' if ok_all else 'GAGAL'}**")
    return "\n".join(L) + "\n", ok_all


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
    report, ok = validate(out)
    (out / "laporan_validasi.md").write_text(report, encoding="utf-8")
    print(report)
    sys.exit(0 if ok else 1)
