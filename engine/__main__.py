"""CLI mesin scan PayRay.

    python -m engine --data data --out hasil            # ranking + antrean + lembar hasil scan
    python -m engine --data data --out hasil --evaluate # + laporan akurasi (butuh data/label/)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import features, score
from . import feedback
from .evaluate import evaluate, report


def scan_sheet(eid: str, r) -> str:
    reasons = [x for x in r.alasan.split(" | ") if x]
    L = [f"# {r.nama}  ·  Risiko {r.kategori_risiko}", "",
         f"{eid} · {r.nama_sektor} · skala {r.skala_usaha} · {int(r.n_pekerja)} pekerja dilaporkan (data sintetis)", "",
         f"**Skor {r.skor:.0f}/100** · keyakinan: **{r.keyakinan}**  ",
         f"Modul — upah {r.modul_upah:.0f} · headcount {r.modul_headcount:.0f} · status {r.modul_status:.0f} · anomali {r.skor_anomali:.0f}", "",
         "## Alasan utama", ""]
    L += [f"{i}. {x}" for i, x in enumerate(reasons, 1)] or ["- (tidak ada aturan yang menyala kuat)"]
    L += ["", f"**Estimasi potensi iuran tak tertagih: ± Rp{r.estimasi_iuran_tak_tertagih:,.0f}/tahun**  ",
          f"(upah · Rp{r.est_upah:,.0f} | pekerja tak terdaftar · Rp{r.est_headcount:,.0f} | pindah PBPU · Rp{r.est_status:,.0f}; "
          f"upah wajar acuan Rp{r.upah_wajar_est:,.0f})", "",
          "_PayRay mengurutkan prioritas. Keputusan pemeriksaan tetap di petugas._"]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="engine")
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--out", type=Path, default=Path("hasil"))
    p.add_argument("--sheets", type=int, default=50, help="jumlah lembar hasil scan teratas")
    p.add_argument("--evaluate", action="store_true")
    a = p.parse_args(argv)
    t0 = time.time()

    f = features.build(features.load(a.data))
    res, S = score.run(f)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "lembar_scan").mkdir(exist_ok=True)
    res.to_csv(a.out / "ranking.csv", index_label="employer_id")
    f.to_csv(a.out / "fitur.csv", index_label="employer_id")
    queue = res[(res.kategori_risiko != "Rendah") & (res.keyakinan != "rendah")]
    queue.sort_values(["prioritas", "estimasi_iuran_tak_tertagih"], ascending=False).to_csv(
        a.out / "antrean_pemeriksaan.csv", index_label="employer_id")
    for eid, r in res.head(a.sheets).iterrows():
        (a.out / "lembar_scan" / f"{eid}.md").write_text(scan_sheet(eid, r), encoding="utf-8")
    (a.out / "ranking_top.json").write_text(json.dumps(
        res.head(200).reset_index(names="employer_id").to_dict(orient="records"), ensure_ascii=False, default=str),
        encoding="utf-8")
    print(f"{len(res):,} badan usaha diskor dalam {time.time() - t0:.1f}s · antrean {len(queue):,} · "
          f"lembar scan {min(a.sheets, len(res))} → {a.out}/")

    if a.evaluate:
        m = evaluate(res, a.data)
        txt = report(m) + feedback.report(feedback.simulate(f, S, res, a.data))
        (a.out / "laporan_akurasi.md").write_text(txt, encoding="utf-8")
        print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
