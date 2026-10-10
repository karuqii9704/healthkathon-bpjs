"""Bangun dashboard PayRay (satu file HTML statis) dari output mesin scan.

    python -m engine --data data --out hasil
    python dashboard/build_dashboard.py --hasil hasil --data data --out dashboard/index.html

Hanya membaca hasil/ (ranking) dan data/referensi/ (nama wilayah). Tidak membaca label.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hasil", type=Path, default=Path("hasil"))
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=HERE / "index.html")
    a = ap.parse_args()

    r = pd.read_csv(a.hasil / "ranking.csv", dtype={"kode_wilayah": str})
    umk = pd.read_csv(a.data / "referensi/umk.csv", dtype={"kode_wilayah": str})
    wil = umk.drop_duplicates("kode_wilayah").set_index("kode_wilayah").nama_wilayah
    r["wilayah"] = r.kode_wilayah.map(wil)

    rows = [{
        "id": x.employer_id, "nama": x.nama, "sektor": x.nama_sektor, "skala": x.skala_usaha,
        "wilayah": x.wilayah, "pekerja": int(x.n_pekerja), "skor": round(float(x.skor), 1),
        "yakin": x.keyakinan, "kat": x.kategori_risiko, "prio": round(float(x.prioritas), 2),
        "mu": int(x.modul_upah), "mh": int(x.modul_headcount), "ms": int(x.modul_status),
        "an": round(float(x.skor_anomali)), "est": int(x.estimasi_iuran_tak_tertagih),
        "eu": int(x.est_upah), "eh": int(x.est_headcount), "es": int(x.est_status),
        "wajar": int(x.upah_wajar_est),
        "alasan": [s for s in str(x.alasan).split(" | ") if s and s != "nan"],
    } for x in r.itertuples()]

    meta = {"dibuat": date.today().isoformat(), "periode": "2025", "n": len(rows)}
    html = (HERE / "template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__META__", json.dumps(meta, ensure_ascii=False))
    a.out.write_text(html, encoding="utf-8")
    print(f"{len(rows):,} badan usaha -> {a.out} ({a.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
