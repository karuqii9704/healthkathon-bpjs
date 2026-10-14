"""Builder snapshot statis GitHub Pages. Stub sampai t25; --dry-run hanya cek argumen."""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        print("build_static: dry-run (stub, diisi di t25)")
        return 0
    print("build_static belum diimplementasikan (t25).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
