"""Kalkulator iuran PPU — dipakai generator untuk label kebenaran dan nanti
oleh dashboard untuk estimasi iuran tak tertagih."""

from __future__ import annotations

import numpy as np

from .config import PLAFON_UPAH_IURAN, TARIF_IURAN_PPU


def iuran_ppu(upah, bulan=12, plafon: int = PLAFON_UPAH_IURAN, tarif: float = TARIF_IURAN_PPU):
    """Iuran PPU (porsi pemberi kerja + pekerja) untuk sejumlah bulan."""
    return np.minimum(np.asarray(upah, dtype=float), plafon) * tarif * np.asarray(bulan)


def estimasi_iuran_tak_tertagih(upah_wajar, upah_dilaporkan, jumlah_pekerja, pekerja_pindah_pbpu=0,
                                plafon: int = PLAFON_UPAH_IURAN, tarif: float = TARIF_IURAN_PPU):
    """Rumus CLAUDE.md: (min(upah_wajar, plafon) - min(upah_dilaporkan, plafon)) x 5% x N x 12,
    ditambah iuran penuh pekerja yang dipindah ke PBPU (dinilai pada upah wajar)."""
    selisih = np.maximum(0, np.minimum(upah_wajar, plafon) - np.minimum(upah_dilaporkan, plafon))
    return selisih * tarif * jumlah_pekerja * 12 + np.minimum(upah_wajar, plafon) * tarif * 12 * pekerja_pindah_pbpu
