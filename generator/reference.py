"""Data referensi publik: UMK per wilayah dan profil sektor (KBLI).

UMK_2024 adalah angka perkiraan dari SK Gubernur 2024 dan harus dicocokkan
ulang dengan sumber resmi. Tahun lain diturunkan dengan faktor kenaikan
rata-rata nasional supaya pola "kenaikan upah = kenaikan UMK" bisa diuji.
"""

from __future__ import annotations

import pandas as pd

# kode, nama wilayah, provinsi, UMK 2024 (perkiraan, verifikasi)
REGIONS = [
    ("3171", "DKI Jakarta", "DKI Jakarta", 5_067_381),
    ("3275", "Kota Bekasi", "Jawa Barat", 5_343_430),
    ("3215", "Kab. Karawang", "Jawa Barat", 5_257_834),
    ("3216", "Kab. Bekasi", "Jawa Barat", 5_219_263),
    ("3273", "Kota Bandung", "Jawa Barat", 4_209_309),
    ("3578", "Kota Surabaya", "Jawa Timur", 4_725_479),
    ("2171", "Kota Batam", "Kepulauan Riau", 4_685_050),
    ("1275", "Kota Medan", "Sumatera Utara", 3_769_082),
    ("7371", "Kota Makassar", "Sulawesi Selatan", 3_643_321),
    ("3374", "Kota Semarang", "Jawa Tengah", 3_243_969),
    ("5171", "Kota Denpasar", "Bali", 3_096_823),
    ("3471", "Kota Yogyakarta", "DI Yogyakarta", 2_492_997),
    ("3320", "Kab. Jepara", "Jawa Tengah", 2_450_915),
    ("3304", "Kab. Banjarnegara", "Jawa Tengah", 2_038_005),
]
# Bobot sampling wilayah (kawasan industri lebih banyak pemberi kerja).
REGION_WEIGHTS = [0.16, 0.08, 0.08, 0.09, 0.08, 0.10, 0.06, 0.07, 0.05, 0.07, 0.04, 0.04, 0.04, 0.04]

# Kenaikan UMK rata-rata nasional ke tahun tersebut (perkiraan).
UMK_GROWTH = {2022: 0.01, 2023: 0.08, 2024: 0.035, 2025: 0.065, 2026: 0.065}

# Rasio upah dikalibrasi agar urutan & level relatif antarsektor mengikuti BPS Sakernas Agustus 2025
# (data_publik/bps/). kbli, nama, padat_karya, rasio median upah/UMK, sigma, porsi pekerja tepat
# di UMK (perusahaan patuh menengah/besar), kenaikan merit rata-rata,
# turnover tahunan, bobot sampling
SECTORS = [
    ("10", "Industri makanan", True, 1.15, 0.25, 0.45, 0.045, 0.22, 0.08),
    ("14", "Industri pakaian jadi", True, 1.03, 0.15, 0.70, 0.030, 0.28, 0.07),
    ("15", "Industri kulit & alas kaki", True, 1.04, 0.15, 0.65, 0.030, 0.26, 0.04),
    ("26", "Industri elektronik", False, 1.35, 0.30, 0.30, 0.050, 0.18, 0.04),
    ("29", "Industri kendaraan bermotor", False, 1.50, 0.30, 0.20, 0.055, 0.12, 0.03),
    ("41", "Konstruksi gedung", False, 1.26, 0.30, 0.35, 0.040, 0.25, 0.07),
    ("47", "Perdagangan eceran", False, 1.12, 0.25, 0.50, 0.035, 0.24, 0.16),
    ("49", "Angkutan darat", False, 1.71, 0.25, 0.35, 0.040, 0.18, 0.06),
    ("56", "Penyediaan makan minum", True, 1.03, 0.20, 0.60, 0.030, 0.30, 0.10),
    ("62", "Pemrograman & konsultansi TI", False, 1.82, 0.40, 0.05, 0.070, 0.15, 0.05),
    ("64", "Jasa keuangan", False, 1.66, 0.40, 0.05, 0.060, 0.10, 0.04),
    ("70", "Konsultansi manajemen", False, 1.44, 0.40, 0.10, 0.060, 0.15, 0.05),
    ("80", "Jasa keamanan & penyediaan tenaga kerja", True, 1.03, 0.12, 0.75, 0.030, 0.30, 0.07),
    ("86", "Jasa kesehatan", False, 1.39, 0.35, 0.20, 0.050, 0.12, 0.07),
    ("85", "Pendidikan", False, 1.15, 0.30, 0.30, 0.040, 0.10, 0.07),
]

# Jumlah pekerja riil awal per skala usaha (min, maks) — besar memakai log-normal.
HEADCOUNT_RANGE = {"mikro": (1, 4), "kecil": (5, 19), "menengah": (20, 99), "besar": (100, 1500)}


def umk_table(years) -> pd.DataFrame:
    """UMK per wilayah per tahun, diturunkan dari UMK 2024."""
    rows = []
    for code, name, prov, base in REGIONS:
        values = {2024: float(base)}
        for y in range(2025, max(years) + 1):
            values[y] = values[y - 1] * (1 + UMK_GROWTH[y])
        for y in range(2023, min(years) - 1, -1):
            values[y] = values[y + 1] / (1 + UMK_GROWTH[y + 1])
        for y in years:
            rows.append((code, name, prov, y, int(round(values[y]))))
    return pd.DataFrame(rows, columns=["kode_wilayah", "nama_wilayah", "provinsi", "tahun", "umk"])


def sector_table() -> pd.DataFrame:
    return pd.DataFrame(
        SECTORS,
        columns=[
            "kbli", "nama_sektor", "padat_karya", "rasio_upah", "sigma_upah",
            "porsi_umk", "kenaikan_merit", "turnover", "bobot",
        ],
    )
