"""Simulasi siklus umpan balik: hasil pemeriksaan petugas menjadi label baru.

Putaran 1: petugas memeriksa top-K skor mesin (aturan + Isolation Forest) ditambah sampel acak
kecil untuk audit. Hanya label badan usaha yang DIPERIKSA yang terbuka.
Putaran 2: model belajar dari hasil pemeriksaan itu, lalu mengurutkan badan usaha yang belum diperiksa.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

NUM_COLS = [
    "n_pekerja", "porsi_tepat_umk", "porsi_bawah_umk", "porsi_atas_umk", "median_rasio_umk", "p90_rasio_umk",
    "porsi_upah_modus", "rasio_benchmark", "porsi_upah_beku", "porsi_naik_sama_umk", "rasio_headcount_oss",
    "tk_oss", "klaster_pbpu_n", "klaster_pbpu_porsi", "tahun_teramati",
]


def matrix(f: pd.DataFrame, S: pd.DataFrame, res: pd.DataFrame) -> pd.DataFrame:
    X = f[NUM_COLS].astype(float).join(S.add_prefix("aturan_"))
    X["skor_anomali"] = res.skor_anomali
    X["skala"] = f.skala_usaha.map({"mikro": 0, "kecil": 1, "menengah": 2, "besar": 3})
    X["padat_karya"] = f.padat_karya.astype(int)
    return X


def simulate(f, S, res, data: Path, k: int = 500, n_random: int = 250, seed: int = 0) -> dict:
    lab = pd.read_csv(data / "label/labels.csv").set_index("employer_id").loc[f.index]
    y = lab.is_violator
    rng = np.random.default_rng(seed)
    order = res.sort_values("prioritas", ascending=False).index
    r1 = list(order[:k])
    rest = order[k:]
    audit = list(rng.choice(rest, size=n_random, replace=False))
    inspected = pd.Index(r1 + audit)
    remaining = f.index.difference(inspected)

    X = matrix(f, S, res)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, l2_regularization=1.0, random_state=seed)
    clf.fit(X.loc[inspected], y.loc[inspected])
    p = pd.Series(clf.predict_proba(X.loc[remaining])[:, 1], index=remaining)

    r2_feedback = p.sort_values(ascending=False).index[:k]
    # prioritas nilai: peluang melanggar x estimasi rupiah (lantai = iuran 1 pekerja UMK setahun)
    floor = 0.05 * 12 * f.loc[remaining, "umk_terakhir"]
    ev = p * np.maximum(res.loc[remaining, "estimasi_iuran_tak_tertagih"], floor)
    r2_value = ev.sort_values(ascending=False).index[:k]
    r2_rules = [e for e in order if e in set(remaining)][:k]
    r2_random = rng.choice(remaining, size=k, replace=False)
    loss = lab.iuran_tak_tertagih_tahun_terakhir
    umkm_ok = (y == 0) & f.skala_usaha.isin(["mikro", "kecil"])

    def stat(ids):
        ids = pd.Index(ids)
        return {"precision": y.loc[ids].mean(), "iuran": loss.loc[ids].sum(),
                "salah_tandai_umkm": umkm_ok.loc[ids].sum() / max(1, umkm_ok.loc[remaining].sum())}

    return {
        "k": k, "n_random": n_random,
        "putaran1_precision": y.loc[r1].mean(),
        "audit_precision": y.loc[audit].mean(),
        "putaran2_umpan_balik": stat(r2_feedback),
        "putaran2_nilai": stat(r2_value),
        "putaran2_aturan_saja": stat(r2_rules),
        "putaran2_acak": stat(r2_random),
        "total_2_putaran_umpan_balik": y.loc[r1].sum() + y.loc[r2_feedback].sum(),
        "total_2_putaran_aturan": y.loc[order[:2 * k]].sum(),
    }


def report(m: dict) -> str:
    a, v, b, c = m["putaran2_umpan_balik"], m["putaran2_nilai"], m["putaran2_aturan_saja"], m["putaran2_acak"]
    return "\n".join([
        "", "## Siklus umpan balik (simulasi)", "",
        f"Putaran 1: petugas memeriksa {m['k']} badan usaha teratas + {m['n_random']} sampel acak untuk audit. "
        f"Precision putaran 1 = {m['putaran1_precision']:.1%} (sampel audit {m['audit_precision']:.1%}). "
        "Hanya hasil pemeriksaan ini yang dipakai sebagai label.", "",
        f"Putaran 2: {m['k']} pemeriksaan berikutnya di antara badan usaha yang belum diperiksa:", "",
        "| Cara memilih | Precision | Iuran tertangkap/thn | Salah tandai UMKM |", "|---|---|---|---|",
        f"| Mesin + belajar dari hasil pemeriksaan | **{a['precision']:.1%}** | Rp{a['iuran']:,.0f} | {a['salah_tandai_umkm']:.1%} |",
        f"| Umpan balik, diurutkan menurut nilai (peluang × estimasi Rp) | {v['precision']:.1%} | Rp{v['iuran']:,.0f} | {v['salah_tandai_umkm']:.1%} |",
        f"| Mesin tanpa umpan balik | {b['precision']:.1%} | Rp{b['iuran']:,.0f} | {b['salah_tandai_umkm']:.1%} |",
        f"| Acak | {c['precision']:.1%} | Rp{c['iuran']:,.0f} | {c['salah_tandai_umkm']:.1%} |",
        "",
        f"Pelanggar ditemukan dalam {2 * m['k']} pemeriksaan: {m['total_2_putaran_umpan_balik']} dengan umpan balik "
        f"vs {m['total_2_putaran_aturan']} tanpa umpan balik.", "",
    ])
