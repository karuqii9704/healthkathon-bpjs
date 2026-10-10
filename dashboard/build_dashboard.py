"""Bangun dashboard PayRay (satu file HTML statis) dari output mesin scan + lapisan ML.

    python -m engine --data data --out hasil
    python -m ml
    python dashboard/build_dashboard.py --hasil hasil --data data --out dashboard/index.html

Membaca hasil/ (ranking, fitur, interval Rp), data/publik + referensi (bukti per tahun), dan ml/artefak
(model untuk browser + laporan validasi). Tidak membaca label.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from ml import model as M  # noqa: E402

TAHUN = [2021, 2022, 2023, 2024, 2025]
HIST = [0, 0.95, 1.05, 1.25, 1.5, 2.0, 3.0, np.inf]  # rasio upah / UMK


def evidence(data: Path, ids: pd.Index) -> dict[str, dict]:
    """Bukti per badan usaha per tahun: median upah, UMK, benchmark, headcount, pindah ke PBPU, histogram upah."""
    e = pd.read_csv(data / "publik/employers.csv", dtype={"kode_wilayah": str}).set_index("employer_id")
    umk = pd.read_csv(data / "referensi/umk.csv", dtype={"kode_wilayah": str})
    bm = pd.read_csv(data / "referensi/benchmark_upah.csv", dtype={"kode_wilayah": str})
    wh = pd.read_csv(data / "publik/wage_history.csv", usecols=["employer_id", "tahun", "upah_dilaporkan", "bulan_aktif"])
    mu = pd.read_csv(data / "publik/mutations.csv", usecols=["employer_id", "tanggal", "jenis", "segmen_tujuan"])

    g = wh.groupby(["employer_id", "tahun"])
    med = g.upah_dilaporkan.median().unstack().reindex(columns=TAHUN)
    hc = (g.bulan_aktif.sum() / 12).unstack().reindex(columns=TAHUN)
    mu["tahun"] = mu.tanggal.str[:4].astype(int)
    k = mu[mu.jenis == "KELUAR_PPU"]
    kel = k.groupby(["employer_id", "tahun"]).size().unstack().reindex(columns=TAHUN).fillna(0)
    pb = k[k.segmen_tujuan == "PBPU"].groupby(["employer_id", "tahun"]).size().unstack().reindex(columns=TAHUN).fillna(0)

    um = umk.pivot_table(index="kode_wilayah", columns="tahun", values="umk").reindex(columns=TAHUN)
    bmk = bm.pivot_table(index=["kbli", "kode_wilayah"], columns="tahun", values="median_upah").reindex(columns=TAHUN)

    last = wh[wh.tahun == TAHUN[-1]].merge(e[["kode_wilayah"]], left_on="employer_id", right_index=True)
    last["r"] = last.upah_dilaporkan / last.kode_wilayah.map(um[TAHUN[-1]])
    last["b"] = pd.cut(last.r, HIST, right=False, labels=False)
    hist = last.groupby(["employer_id", "b"]).size().unstack().reindex(columns=range(len(HIST) - 1)).fillna(0)

    def arr(df, i, nd=0):
        if i not in df.index:
            return [0] * len(df.columns)
        v = df.loc[i].to_numpy(dtype=float)
        return [None if np.isnan(x) else (round(x, nd) if nd else int(round(x))) for x in v]

    out = {}
    for i in ids:
        kw, kb = e.at[i, "kode_wilayah"], e.at[i, "kbli"]
        out[i] = {"m": arr(med, i), "u": arr(um, kw), "b": arr(bmk, (kb, kw)) if (kb, kw) in bmk.index else [None] * 5,
                  "h": arr(hc, i, 1), "o": int(e.at[i, "tk_oss"]), "k": arr(kel, i), "p": arr(pb, i), "d": arr(hist, i)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hasil", type=Path, default=ROOT / "hasil")
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--artefak", type=Path, default=ROOT / "ml/artefak")
    ap.add_argument("--out", type=Path, default=HERE / "index.html")
    a = ap.parse_args()

    r = pd.read_csv(a.hasil / "ranking.csv", dtype={"kode_wilayah": str}).set_index("employer_id")
    f = pd.read_csv(a.hasil / "fitur.csv", dtype={"kode_wilayah": str}).set_index("employer_id").loc[r.index]
    ml = pd.read_csv(a.hasil / "ml_prediksi.csv").set_index("employer_id").loc[r.index]
    umk = pd.read_csv(a.data / "referensi/umk.csv", dtype={"kode_wilayah": str})
    wil = umk.drop_duplicates("kode_wilayah").set_index("kode_wilayah").nama_wilayah
    model = json.loads((a.artefak / "model_payray.json").read_text(encoding="utf-8"))
    val = json.loads((a.artefak / "validasi.json").read_text(encoding="utf-8"))
    X = M.matrix(f)
    ev = evidence(a.data, r.index)

    def num(v):
        return None if pd.isna(v) else float(f"{v:.6g}")

    rows = []
    for x in r.itertuples():
        i = x.Index
        rows.append({
            "id": i, "nama": x.nama, "sektor": x.nama_sektor, "skala": x.skala_usaha,
            "wilayah": wil.get(x.kode_wilayah, x.kode_wilayah), "pekerja": int(x.n_pekerja), "skor": round(float(x.skor), 1),
            "yakin": x.keyakinan, "kat": x.kategori_risiko, "prio": round(float(x.prioritas), 2),
            "mu": int(x.modul_upah), "mh": int(x.modul_headcount), "ms": int(x.modul_status),
            "an": round(float(x.skor_anomali)), "est": int(x.estimasi_iuran_tak_tertagih),
            "eu": int(x.est_upah), "eh": int(x.est_headcount), "es": int(x.est_status), "wajar": int(x.upah_wajar_est),
            "alasan": [s for s in str(x.alasan).split(" | ") if s and s != "nan"],
            "pr": float(ml.at[i, "persentil_aturan"]), "insp": int(ml.at[i, "diperiksa"]),
            "lo": int(ml.at[i, "rp_lo"]), "md": int(ml.at[i, "rp_med"]), "hi": int(ml.at[i, "rp_hi"]),
            "x": [num(v) for v in X.loc[i].to_numpy()], "ev": ev[i],
        })
        if rows[-1]["insp"]:
            rows[-1]["pmo"], rows[-1]["pgo"] = float(ml.at[i, "p_ml"]), float(ml.at[i, "p_gabungan"])

    # parity check: nilai acuan dari evaluator Python, dicocokkan ulang oleh browser saat halaman dibuka
    probe = list(r.index[:3]) + list(r.index[-2:])
    parity = [{"id": i, "raw": M.contributions(model, X.loc[i].to_numpy())[0]} for i in probe]

    meta = {"dibuat": date.today().isoformat(), "periode": "2025", "n": len(rows), "tahun": TAHUN,
            "hist": ["<0,95", "≈1", "1,05+", "1,25+", "1,5+", "2+", "3+"], "parity": parity}
    html = (HERE / "template.html").read_text(encoding="utf-8")
    for key, obj in [("__DATA__", rows), ("__META__", meta), ("__MODEL__", model), ("__VAL__", val)]:
        html = html.replace(key, json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    a.out.write_text(html, encoding="utf-8")
    print(f"{len(rows):,} badan usaha -> {a.out} ({a.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
