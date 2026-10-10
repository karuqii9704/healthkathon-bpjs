"""Data quality checks untuk data input mesin scan (data/publik + data/referensi).

Skor hanya bisa dipercaya kalau datanya bisa dipercaya: setiap periode scan diawali pemeriksaan ini.
Status: lulus / peringatan (perlu dilihat petugas data) / gagal (scan tidak boleh jalan).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SKEMA = {
    "employers": ["employer_id", "nama", "kbli", "kode_wilayah", "skala_usaha", "tahun_berdiri", "tk_oss"],
    "workers": ["worker_id", "employer_id", "tgl_masuk", "tgl_keluar", "tahun_lahir"],
    "wage_history": ["worker_id", "employer_id", "tahun", "upah_dilaporkan", "bulan_aktif"],
    "mutations": ["worker_id", "employer_id", "tanggal", "jenis", "segmen_tujuan", "alasan"],
}


def _row(nama: str, bad: int, total: int, warn_frac: float = 0.0, fail_frac: float = 0.0, ket: str = "") -> dict:
    frac = bad / max(1, total)
    status = "gagal" if bad and frac > fail_frac else "peringatan" if bad and frac > warn_frac else "lulus"
    temuan = f"{bad:,} dari {total:,} baris ({frac:.2%})".replace(",", ".") if bad else f"0 dari {total:,} baris".replace(",", ".")
    return {"nama": nama, "status": status, "temuan": temuan + (f" · {ket}" if ket else ""), "n": int(bad), "total": int(total)}


def run_checks(data: Path) -> list[dict]:
    p, ref = data / "publik", data / "referensi"
    dt = {"employer_id": str, "worker_id": str, "kode_wilayah": str}
    t = {k: pd.read_csv(p / f"{k}.csv", dtype=dt, low_memory=False) for k in SKEMA}
    umk = pd.read_csv(ref / "umk.csv", dtype={"kode_wilayah": str})
    sek = pd.read_csv(ref / "sektor.csv")
    out = []

    miss = [f"{k}.{c}" for k, cols in SKEMA.items() for c in cols if c not in t[k].columns]
    out.append({"nama": "Skema kolom wajib", "status": "gagal" if miss else "lulus",
                "temuan": ("hilang: " + ", ".join(miss)) if miss else f"{sum(map(len, SKEMA.values()))} kolom di 4 tabel lengkap",
                "n": len(miss), "total": sum(map(len, SKEMA.values()))})

    e, w, wh, mu = t["employers"], t["workers"], t["wage_history"], t["mutations"]
    out.append(_row("ID badan usaha unik", int(e.employer_id.duplicated().sum()), len(e)))
    out.append(_row("ID pekerja unik per badan usaha", int(w.duplicated(["worker_id", "employer_id"]).sum()), len(w)))
    kunci = sum(int(t[k][c].isna().sum()) for k, c in
                [("employers", "employer_id"), ("workers", "worker_id"), ("wage_history", "upah_dilaporkan"), ("mutations", "jenis")])
    out.append(_row("Nilai kosong di kolom kunci", kunci, len(e) + len(w) + len(wh) + len(mu)))

    eids = set(e.employer_id)
    out.append(_row("Pekerja → badan usaha terdaftar (referential integrity)", int((~w.employer_id.isin(eids)).sum()), len(w)))
    pk = set(zip(w.worker_id, w.employer_id))
    out.append(_row("Riwayat upah → pekerja terdaftar", int(sum((a, b) not in pk for a, b in zip(wh.worker_id, wh.employer_id))), len(wh)))
    out.append(_row("Mutasi → pekerja terdaftar", int(sum((a, b) not in pk for a, b in zip(mu.worker_id, mu.employer_id))), len(mu)))

    out.append(_row("Upah dilaporkan > 0", int((wh.upah_dilaporkan <= 0).sum()), len(wh)))
    out.append(_row("Bulan aktif dalam 1–12", int((~wh.bulan_aktif.between(1, 12)).sum()), len(wh)))
    out.append(_row("Duplikat upah (pekerja, badan usaha, tahun)", int(wh.duplicated(["worker_id", "employer_id", "tahun"]).sum()), len(wh)))

    m, k = pd.to_datetime(w.tgl_masuk, errors="coerce"), pd.to_datetime(w.tgl_keluar, errors="coerce")
    out.append(_row("Tanggal keluar ≥ tanggal masuk", int((k < m).sum()), len(w)))
    usia = m.dt.year - w.tahun_lahir
    out.append(_row("Usia saat masuk kerja 15–70 tahun", int((~usia.between(15, 70)).sum()), len(w), warn_frac=0.0, fail_frac=0.05))
    out.append(_row("Wilayah ada di tabel UMK", int((~e.kode_wilayah.isin(set(umk.kode_wilayah))).sum()), len(e)))
    out.append(_row("KBLI ada di tabel sektor", int((~e.kbli.isin(set(sek.kbli))).sum()), len(e)))

    j = wh.merge(e[["employer_id", "kode_wilayah"]], on="employer_id").merge(umk[["kode_wilayah", "tahun", "umk"]],
                                                                             on=["kode_wilayah", "tahun"], how="left")
    out.append(_row("UMK tersedia untuk setiap tahun upah", int(j.umk.isna().sum()), len(j)))
    ekstrem = int((j.upah_dilaporkan > 40 * j.umk).sum())
    out.append(_row("Upah ekstrem (> 40× UMK)", ekstrem, len(j), warn_frac=0.0, fail_frac=0.01,
                    ket="bisa direksi/eksekutif sah; tidak memengaruhi iuran karena plafon Rp12 jt"))
    out.append(_row("Tahun berdiri ≤ tahun data", int((e.tahun_berdiri > wh.tahun.max()).sum()), len(e)))
    return out
