"""Parameter generator data sintetis PayRay.

Semua angka regulasi di sini WAJIB diverifikasi ulang sebelum submit
(lihat bagian "Cek regulasi" di CLAUDE.md).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


# --- Regulasi (verifikasi sebelum submit) ---------------------------------
# Iuran PPU = 5% upah: 4% pemberi kerja, 1% pekerja (Perpres 64/2020).
TARIF_IURAN_PPU = 0.05
TARIF_PEMBERI_KERJA = 0.04
# Batas atas upah sebagai dasar perhitungan iuran PPU (Perpres 64/2020).
PLAFON_UPAH_IURAN = 12_000_000
# Usaha mikro & kecil dikecualikan dari upah minimum (PP 36/2021); upah
# berdasarkan kesepakatan. Lantai sintetis agar upah tetap masuk akal.
LANTAI_UPAH_UMKM_RASIO = 0.55


@dataclass
class Config:
    n_employers: int = 5000
    violation_rate: float = 0.15
    hard_negative_rate: float = 0.12
    years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025)
    seed: int = 42
    # Seed injeksi dirahasiakan oleh anggota tim yang menyisipkan pelanggaran.
    inject_seed: int | None = None

    # Proporsi skala usaha di antara pemberi kerja PPU.
    scale_weights: dict[str, float] = field(
        default_factory=lambda: {"mikro": 0.35, "kecil": 0.35, "menengah": 0.22, "besar": 0.08}
    )
    # Bobot modus pelanggaran & peluang violator punya 2 modus sekaligus.
    mode_weights: dict[str, float] = field(
        default_factory=lambda: {"upah": 0.5, "headcount": 0.3, "status": 0.2}
    )
    p_two_modes: float = 0.25
    p_easy: float = 0.5
    # Bobot arketipe hard negative (badan usaha patuh yang tampak mencurigakan).
    hard_negative_weights: dict[str, float] = field(
        default_factory=lambda: {
            "padat_karya_umk": 0.35,
            "umkm_bawah_umk": 0.35,
            "phk_massal_sah": 0.15,
            "upah_seragam_sah": 0.15,
        }
    )
    # Sel benchmark upah (simulasi Sakernas BPS) dengan sampel < ini disensor.
    benchmark_min_sample: int = 30

    def to_public_dict(self) -> dict:
        d = asdict(self)
        d.pop("inject_seed")
        d["years"] = list(self.years)
        return d
