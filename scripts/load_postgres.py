"""Muat CSV hasil generator ke PostgreSQL (COPY, cepat untuk jutaan baris).

    pip install "psycopg[binary]"
    python scripts/load_postgres.py --data data --dsn postgresql://user:pass@localhost:5432/payray [--with-labels]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

# urutan penting karena foreign key
TABLES = [
    ("referensi.umk", "referensi/umk.csv"),
    ("referensi.sektor", "referensi/sektor.csv"),
    ("referensi.benchmark_upah", "referensi/benchmark_upah.csv"),
    ("publik.employers", "publik/employers.csv"),
    ("publik.workers", "publik/workers.csv"),
    ("publik.wage_history", "publik/wage_history.csv"),
    ("publik.mutations", "publik/mutations.csv"),
]
LABEL_TABLES = [
    ("label.labels", "label/labels.csv"),
    ("label.hidden_workers", "label/hidden_workers.csv"),
    ("label.moved_workers", "label/moved_workers.csv"),
    ("label.upah_riil", "label/upah_riil.csv"),
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--dsn", required=True)
    p.add_argument("--with-labels", action="store_true", help="hanya untuk database evaluator")
    a = p.parse_args()

    schema = (Path(__file__).parent.parent / "db" / "schema.sql").read_text(encoding="utf-8")
    tables = TABLES + (LABEL_TABLES if a.with_labels else [])
    with psycopg.connect(a.dsn) as conn, conn.cursor() as cur:
        cur.execute(schema)
        for table, _ in reversed(tables):
            cur.execute(f"TRUNCATE {table} CASCADE")
        for table, rel in tables:
            path = a.data / rel
            header = path.open(encoding="utf-8").readline().strip()
            with path.open("rb") as f, cur.copy(f"COPY {table} ({header}) FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
                while chunk := f.read(1 << 20):
                    cp.write(chunk)
            print(f"{table:28s} <- {rel}")
        conn.commit()


if __name__ == "__main__":
    main()
