"""Menulis output ke CSV dengan pemisahan akses:

  <out>/publik/     -> boleh dibaca tim model (data "yang dilihat BPJS")
  <out>/referensi/  -> data publik pembanding (UMK, sektor, benchmark upah)
  <out>/label/      -> HANYA untuk evaluator / penyisip pelanggaran
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .config import PLAFON_UPAH_IURAN, TARIF_IURAN_PPU, Config
from .inject import Injected
from .world import World


def _mutations(workers: pd.DataFrame) -> pd.DataFrame:
    join = pd.DataFrame({
        "worker_id": workers.worker_id, "employer_id": workers.employer_id, "tanggal": workers.tgl_masuk,
        "jenis": "DAFTAR_PPU", "segmen_tujuan": None, "tgl_segmen_baru": None, "alasan": None,
    })
    out = workers[workers.tgl_keluar.notna()]
    new_seg = [
        t + timedelta(days=int(j)) if isinstance(j, (int, float, np.integer, np.floating)) and not pd.isna(j) else None
        for t, j in zip(out.tgl_keluar, out.jeda_hari)
    ]
    leave = pd.DataFrame({
        "worker_id": out.worker_id, "employer_id": out.employer_id, "tanggal": out.tgl_keluar,
        "jenis": "KELUAR_PPU", "segmen_tujuan": out.segmen_tujuan, "tgl_segmen_baru": new_seg,
        "alasan": out.alasan_keluar,
    })
    m = pd.concat([join, leave], ignore_index=True).sort_values(["tanggal", "worker_id"], kind="stable")
    m.insert(0, "mutation_id", [f"M{i + 1:07d}" for i in range(len(m))])
    return m.reset_index(drop=True)


def _benchmark(world: World, cfg: Config, rng) -> pd.DataFrame:
    """Simulasi tabel median upah sektor x wilayah ala Sakernas BPS:
    dihitung dari upah riil (termasuk pekerja tak terdaftar) + galat survei;
    sel bersampel kecil disensor supaya skor di wilayah itu berkeyakinan rendah."""
    w = world.wages.merge(world.employers[["employer_id", "kbli", "kode_wilayah"]], on="employer_id")
    # survei hanya mencuplik ~20% pekerja
    w = w[rng.random(len(w)) < 0.2]
    g = w.groupby(["kbli", "kode_wilayah", "tahun"]).upah_riil.agg(["median", "size"]).reset_index()
    g["median_upah"] = (g["median"] * rng.normal(1.0, 0.03, len(g)) / 1000).round() * 1000
    g.loc[g["size"] < cfg.benchmark_min_sample, "median_upah"] = np.nan
    return g.rename(columns={"size": "n_sampel"})[["kbli", "kode_wilayah", "tahun", "median_upah", "n_sampel"]]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_all(world: World, inj: Injected, cfg: Config, out: Path) -> dict:
    pub, ref, lab = out / "publik", out / "referensi", out / "label"
    for d in (pub, ref, lab):
        d.mkdir(parents=True, exist_ok=True)

    workers_pub = inj.workers[["worker_id", "employer_id", "tgl_masuk", "tgl_keluar", "tahun_lahir", "jenis_kelamin"]]
    files = {
        pub / "employers.csv": world.employers,
        pub / "workers.csv": workers_pub,
        pub / "wage_history.csv": inj.wages,
        pub / "mutations.csv": _mutations(inj.workers),
        ref / "umk.csv": world.umk,
        ref / "sektor.csv": world.sectors[["kbli", "nama_sektor", "padat_karya"]],
        ref / "benchmark_upah.csv": _benchmark(world, cfg, np.random.default_rng(cfg.seed + 1)),
        lab / "labels.csv": inj.labels,
        lab / "hidden_workers.csv": inj.hidden_workers,
        lab / "moved_workers.csv": inj.moved_workers,
        lab / "upah_riil.csv": inj.true_wages,
    }
    for path, df in files.items():
        df.to_csv(path, index=False)

    manifest = {
        "dibuat": datetime.now().isoformat(timespec="seconds"),
        "config": cfg.to_public_dict(),
        "regulasi": {"tarif_iuran_ppu": TARIF_IURAN_PPU, "plafon_upah_iuran": PLAFON_UPAH_IURAN},
        "baris": {str(p.relative_to(out)).replace("\\", "/"): len(df) for p, df in files.items()
                  if not p.is_relative_to(lab)},
        "sha256": {str(p.relative_to(out)).replace("\\", "/"): _sha(p) for p in files
                   if not p.is_relative_to(lab)},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    # Seed injeksi hanya disimpan di folder label.
    (lab / "manifest_injeksi.json").write_text(
        json.dumps({"inject_seed": cfg.inject_seed,
                    "baris": {p.name: len(df) for p, df in files.items() if p.is_relative_to(lab)}}, indent=2),
        encoding="utf-8")
    return manifest
