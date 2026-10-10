"""CLI: python -m generator --out data [--n-employers 5000] [--seed 42] [--inject-seed RAHASIA]"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
from pathlib import Path

from .config import Config
from .export import write_all
from .inject import inject
from .validate import validate
from .world import build_world


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="generator", description="Generator data sintetis PayRay")
    p.add_argument("--out", type=Path, default=Path("data"))
    p.add_argument("--n-employers", type=int, default=5000)
    p.add_argument("--violation-rate", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42, help="seed dunia (boleh diketahui tim)")
    p.add_argument("--inject-seed", type=int, default=None,
                   help="seed penyisipan pelanggaran (rahasia; default acak)")
    p.add_argument("--skip-validate", action="store_true")
    a = p.parse_args(argv)

    cfg = Config(n_employers=a.n_employers, violation_rate=a.violation_rate, seed=a.seed,
                 inject_seed=a.inject_seed if a.inject_seed is not None else secrets.randbelow(2**31))
    t0 = time.time()
    print(f"[1/4] Membangun dunia sintetis ({cfg.n_employers} badan usaha)...")
    world = build_world(cfg)
    print(f"      {len(world.workers):,} pekerja riil, {len(world.wages):,} baris upah ({time.time() - t0:.1f}s)")
    print("[2/4] Menyisipkan pelanggaran (blind)...")
    inj = inject(world, cfg)
    print(f"[3/4] Menulis CSV ke {a.out}/ ...")
    write_all(world, inj, cfg, a.out)
    if a.skip_validate:
        print(f"Selesai dalam {time.time() - t0:.1f}s")
        return 0
    print("[4/4] Validasi...")
    report, ok = validate(a.out)
    (a.out / "laporan_validasi.md").write_text(report, encoding="utf-8")
    print(f"      Laporan: {a.out / 'laporan_validasi.md'} — {'LULUS' if ok else 'GAGAL'} ({time.time() - t0:.1f}s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
