"""Aturan bisnis transparan. Setiap aturan menghasilkan skor 0..1 dan kalimat alasan
yang bisa dibaca petugas, dibedakan per skala usaha (UMKM dikecualikan dari UMK, PP 36/2021)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clip01(x):
    return np.clip(x, 0, 1)


def _pct(x) -> str:
    return f"{x:.0%}"


def peer_median(f: pd.DataFrame, col: str, by=("kbli", "skala_usaha"), min_n: int = 15) -> pd.Series:
    """Median fitur di antara badan usaha sejenis (sektor x skala), fallback ke skala saja."""
    fine = f.groupby(list(by))[col].transform("median")
    n = f.groupby(list(by))[col].transform("count")
    coarse = f.groupby("skala_usaha")[col].transform("median")
    return fine.where(n >= min_n, coarse)


RULES = {
    # nama: (modul, bobot)
    "bunching_umk": ("upah", 0.8),
    "naik_sama_umk": ("upah", 0.5),
    "upah_beku": ("upah", 0.9),
    "bawah_umk_wajib": ("upah", 0.9),
    "upah_atas_rendah": ("upah", 0.6),
    "headcount_oss": ("headcount", 0.9),
    "klaster_pbpu": ("status", 0.9),
}


def apply_rules(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Kembalikan (skor per aturan, alasan per aturan)."""
    S = pd.DataFrame(0.0, index=f.index, columns=list(RULES))
    R = pd.DataFrame("", index=f.index, columns=list(RULES))
    wajib_umk = ~f.umkm
    enough = f.n_pekerja >= 5

    # 1) bunching di UMK dibanding sektor sejenis
    peer = peer_median(f, "porsi_tepat_umk")
    excess = f.porsi_tepat_umk - peer
    s = _clip01((excess - 0.1) / 0.4) * enough * np.where(f.umkm, 0.5, 1.0)
    # usaha padat karya yang sah tetap punya supervisor/staf di atas UMK; laporan yang menaruh
    # SEMUA orang di UMK (atau di bawahnya) tidak masuk akal untuk usaha >= 10 orang
    flat = _clip01((0.05 - f.porsi_atas_umk.fillna(1)) / 0.03) * (f.n_pekerja >= 10) * (f.porsi_tepat_umk >= 0.5)
    S["bunching_umk"] = np.maximum(s * 0.75, flat * np.where(f.umkm, 0.6, 1.0))
    R["bunching_umk"] = [
        f"{_pct(a)} karyawan dilaporkan tepat di UMK (median sektor sejenis {_pct(b)})"
        + ("; tidak satu pun, termasuk supervisor/staf, dilaporkan di atas UMK" if c == 0
           else f"; hanya {_pct(c)} di atas UMK, termasuk supervisor/staf" if c <= 0.05 else "")
        for a, b, c in zip(f.porsi_tepat_umk, peer, f.porsi_atas_umk.fillna(1))]

    # 2) kenaikan upah selalu persis = kenaikan UMK (untuk pekerja yang upahnya di atas UMK)
    p = f.porsi_naik_sama_umk.fillna(0)
    peer = peer_median(f.assign(_p=p), "_p")
    S["naik_sama_umk"] = _clip01((p - peer - 0.2) / 0.5) * enough
    R["naik_sama_umk"] = [f"{_pct(a)} kenaikan upah karyawan di atas UMK persis sama dengan kenaikan UMK"
                          for a in p]

    # 3) upah beku saat UMK naik
    p = f.porsi_upah_beku.fillna(0)
    peer = peer_median(f.assign(_p=p), "_p")
    S["upah_beku"] = _clip01((p - peer - 0.15) / 0.45) * (f.pasangan_kenaikan >= 3)
    R["upah_beku"] = [f"{_pct(a)} pekerja tidak naik upah walau UMK naik (sektor sejenis {_pct(b)})"
                      for a, b in zip(p, peer)]

    # 4) di bawah UMK padahal skala menengah/besar (wajib UMK)
    S["bawah_umk_wajib"] = _clip01(f.porsi_bawah_umk / 0.3) * wajib_umk
    R["bawah_umk_wajib"] = [f"{_pct(a)} karyawan dilaporkan di bawah UMK, padahal usaha {sk} wajib membayar ≥ UMK"
                            for a, sk in zip(f.porsi_bawah_umk, f.skala_usaha)]

    # 5) upah bagian atas jauh lebih rendah dari sektor sejenis (pemotongan selektif)
    peer = peer_median(f, "p90_rasio_umk", by=("kbli", "skala_usaha", "kode_wilayah"), min_n=10)
    short = 1 - f.p90_rasio_umk / peer
    bm_short = (1 - f.rasio_benchmark).where(f.benchmark_upah.notna(), 0)
    s = _clip01((short - 0.1) / 0.3) * 0.7 + _clip01((bm_short - 0.15) / 0.4) * 0.3
    S["upah_atas_rendah"] = s * (f.n_pekerja >= 8) * wajib_umk
    R["upah_atas_rendah"] = [
        f"Upah 10% teratas {r:.2f}× UMK, sektor & wilayah sejenis {pr:.2f}× UMK"
        + (f"; median upah {_pct(rb)} dari benchmark sektor" if pd.notna(rb) else "")
        for r, pr, rb in zip(f.p90_rasio_umk, peer, f.rasio_benchmark)
    ]

    # 6) pekerja terdaftar jauh di bawah rencana tenaga kerja OSS
    ratio = f.rasio_headcount_oss
    reliab = np.clip((f.tk_oss - 2) / 8, 0, 1)  # usaha 1-3 orang: rasio sangat kasar
    S["headcount_oss"] = _clip01((0.8 - ratio) / 0.35).fillna(0) * reliab
    R["headcount_oss"] = [f"Rata-rata pekerja terdaftar {a:.0f} orang, rencana tenaga kerja di OSS {int(b)} orang ({_pct(r) if pd.notna(r) else '-'})"
                          for a, b, r in zip(f.n_pekerja_awal, f.tk_oss, ratio)]

    # 7) klaster keluar PPU lalu cepat terdaftar PBPU, bukan karena PHK
    s = _clip01((f.klaster_pbpu_porsi - 0.06) / 0.2) * (f.klaster_pbpu_n >= 3)
    S["klaster_pbpu"] = s
    R["klaster_pbpu"] = [
        f"{int(n)} pekerja keluar PPU lalu terdaftar PBPU ≤30 hari dalam 3 bulan ({_pct(p)} tenaga kerja), alasan bukan PHK"
        for n, p in zip(f.klaster_pbpu_n, f.klaster_pbpu_porsi)
    ]
    return S.fillna(0), R
