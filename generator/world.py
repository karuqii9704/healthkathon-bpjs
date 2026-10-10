"""Tahap 1: membangun "dunia nyata" sintetis tanpa pelanggaran.

Di dunia ini setiap pemberi kerja melaporkan upah dan pekerja dengan jujur.
Sebagian sengaja dibuat tampak mencurigakan (hard negative) walaupun patuh.
Pelanggaran baru disisipkan di tahap 2 (inject.py) oleh orang lain.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import LANTAI_UPAH_UMKM_RASIO, Config
from .reference import HEADCOUNT_RANGE, REGION_WEIGHTS, REGIONS, sector_table, umk_table

_NAME_A = ["Sinar", "Maju", "Karya", "Mitra", "Cahaya", "Bumi", "Sumber", "Tunas", "Prima", "Graha",
           "Bintang", "Mega", "Surya", "Anugerah", "Putra", "Duta", "Nusa", "Indo", "Harapan", "Berkah"]
_NAME_B = ["Abadi", "Jaya", "Sejahtera", "Makmur", "Mandiri", "Lestari", "Sentosa", "Perkasa", "Utama",
           "Gemilang", "Bersama", "Persada", "Santosa", "Raya", "Agung", "Mulia", "Langgeng", "Wijaya"]


@dataclass
class World:
    employers: pd.DataFrame
    archetypes: pd.DataFrame  # employer_id -> hard negative type (rahasia)
    workers: pd.DataFrame
    wages: pd.DataFrame
    umk: pd.DataFrame
    sectors: pd.DataFrame


class _IdGen:
    """Pseudonim pekerja: hash berkunci, tidak bisa dibalik tanpa kunci."""

    def __init__(self, seed: int):
        self._key = hashlib.sha256(f"payray-salt-{seed}".encode()).digest()[:32]
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return "P" + hashlib.blake2b(str(self._n).encode(), key=self._key, digest_size=8).hexdigest()


def _round_k(x: float) -> int:
    return int(round(x / 1000.0)) * 1000


def _rand_date(rng, year: int, start_month: int = 1, end_month: int = 12) -> date:
    lo = date(year, start_month, 1)
    hi = date(year, end_month, 28)
    return lo + timedelta(days=int(rng.integers(0, (hi - lo).days + 1)))


def _months_active(start: date, end: date | None, year: int) -> int:
    if start.year > year or (end is not None and end.year < year):
        return 0
    s = start.month if start.year == year else 1
    e = end.month if end is not None and end.year == year else 12
    return e - s + 1


def _initial_headcount(rng, scale: str) -> int:
    lo, hi = HEADCOUNT_RANGE[scale]
    if scale == "besar":
        return int(np.clip(rng.lognormal(math.log(220), 0.7), lo, hi))
    return int(rng.integers(lo, hi + 1))


def _assign_hard_negatives(cfg: Config, rng, emp: pd.DataFrame, sectors: pd.DataFrame) -> pd.Series:
    n_hn = int(round(cfg.n_employers * cfg.hard_negative_rate))
    idx = rng.choice(len(emp), size=n_hn, replace=False)
    types = list(cfg.hard_negative_weights)
    probs = np.array(list(cfg.hard_negative_weights.values()))
    chosen = rng.choice(types, size=n_hn, p=probs / probs.sum())
    padat = sectors.loc[sectors.padat_karya, "kbli"].tolist()

    arche = pd.Series([None] * len(emp), dtype=object)
    for i, t in zip(idx, chosen):
        arche.iat[i] = t
        if t == "padat_karya_umk":
            emp.at[i, "kbli"] = rng.choice(padat)
            emp.at[i, "skala_usaha"] = rng.choice(["menengah", "besar"], p=[0.7, 0.3])
        elif t == "umkm_bawah_umk":
            emp.at[i, "skala_usaha"] = rng.choice(["mikro", "kecil"])
        elif t == "phk_massal_sah":
            emp.at[i, "skala_usaha"] = rng.choice(["menengah", "besar"], p=[0.7, 0.3])
        elif t == "upah_seragam_sah":
            emp.at[i, "skala_usaha"] = rng.choice(["kecil", "menengah"], p=[0.7, 0.3])
    return arche


def _employer_name(rng, scale: str) -> str:
    prefix = rng.choice(["PT", "CV", "UD"], p=[0.3, 0.5, 0.2]) if scale in ("mikro", "kecil") else "PT"
    return f"{prefix} {rng.choice(_NAME_A)} {rng.choice(_NAME_B)}"


def build_world(cfg: Config) -> World:
    rng = np.random.default_rng(cfg.seed)
    years = list(cfg.years)
    umk = umk_table(years)
    umk_map = {(r.kode_wilayah, r.tahun): r.umk for r in umk.itertuples()}
    sectors = sector_table()
    sec_by_kbli = sectors.set_index("kbli")

    n = cfg.n_employers
    scales = list(cfg.scale_weights)
    sp = np.array(list(cfg.scale_weights.values()))
    rw = np.array(REGION_WEIGHTS)
    sw = sectors.bobot.to_numpy()
    emp = pd.DataFrame({
        "employer_id": [f"BU{i + 1:05d}" for i in range(n)],
        "kbli": rng.choice(sectors.kbli, size=n, p=sw / sw.sum()),
        "kode_wilayah": rng.choice([r[0] for r in REGIONS], size=n, p=rw / rw.sum()),
        "skala_usaha": rng.choice(scales, size=n, p=sp / sp.sum()),
    })
    arche = _assign_hard_negatives(cfg, rng, emp, sectors)

    ids = _IdGen(cfg.seed)
    worker_rows: list[tuple] = []
    wage_rows: list[tuple] = []
    extra = {"nama": [], "tahun_berdiri": [], "tk_oss": []}

    for i, e in enumerate(emp.itertuples(index=False)):
        sec = sec_by_kbli.loc[e.kbli]
        a = arche.iat[i]
        founded = years[0] - int(rng.exponential(9)) - 1 if rng.random() < 0.9 else int(rng.choice(years))
        n0 = _initial_headcount(rng, e.skala_usaha)
        extra["nama"].append(_employer_name(rng, e.skala_usaha))
        extra["tahun_berdiri"].append(founded)
        # Rencana tenaga kerja yang dideklarasikan di NIB/OSS (proksi skala usaha).
        extra["tk_oss"].append(max(1, int(round(n0 * rng.lognormal(0, 0.15)))))
        _simulate_employer(cfg, rng, ids, e, sec, a, founded, n0, umk_map, worker_rows, wage_rows)

    emp = emp.assign(**extra)
    emp = emp.merge(sectors[["kbli", "nama_sektor", "padat_karya"]], on="kbli", how="left")
    emp = emp[["employer_id", "nama", "kbli", "nama_sektor", "padat_karya", "kode_wilayah",
               "skala_usaha", "tahun_berdiri", "tk_oss"]]

    workers = pd.DataFrame(worker_rows, columns=[
        "worker_id", "employer_id", "tgl_masuk", "tgl_keluar", "segmen_tujuan", "jeda_hari",
        "alasan_keluar", "tahun_lahir", "jenis_kelamin",
    ])
    wages = pd.DataFrame(wage_rows, columns=["worker_id", "employer_id", "tahun", "upah_riil", "bulan_aktif"])
    archetypes = pd.DataFrame({"employer_id": emp.employer_id, "hard_negative_type": arche.values})
    archetypes = archetypes.dropna().reset_index(drop=True)
    return World(emp, archetypes, workers, wages, umk, sectors)


def _simulate_employer(cfg, rng, ids, e, sec, archetype, founded, n0, umk_map, worker_rows, wage_rows):
    years = [y for y in cfg.years if y >= founded]
    umkm = e.skala_usaha in ("mikro", "kecil")
    porsi_umk = 0.2 if umkm else sec.porsi_umk
    promo = 0.08
    if archetype == "padat_karya_umk":
        porsi_umk, promo = rng.uniform(0.85, 0.97), 0.02
    uniform_wage = None
    if archetype == "upah_seragam_sah":
        uniform_wage = _round_k(umk_map[(e.kode_wilayah, years[0])] * rng.uniform(1.0, 1.12))

    def new_wage(y):
        u = umk_map[(e.kode_wilayah, y)]
        if uniform_wage is not None:
            return uniform_wage, False
        if archetype == "umkm_bawah_umk":
            return _round_k(u * float(np.clip(rng.lognormal(math.log(0.72), 0.08), 0.55, 0.98))), False
        if rng.random() < porsi_umk:
            return u, True
        if umkm:
            base = {"mikro": 0.85, "kecil": 0.95}[e.skala_usaha] * (1 + (sec.rasio_upah - 1) * 0.5)
            return _round_k(u * max(LANTAI_UPAH_UMKM_RASIO, rng.lognormal(math.log(base), 0.2))), False
        excess = max(0.02, sec.rasio_upah - 1) * rng.lognormal(0, sec.sigma_upah * 2)
        return _round_k(min(u * (1 + excess), 60_000_000)), False

    # state pekerja aktif: dict id -> [record, wage, at_umk]
    active: dict[str, list] = {}

    def hire(start: date, y: int):
        wid = ids.next()
        w, at = new_wage(y)
        rec = {
            "worker_id": wid, "employer_id": e.employer_id, "tgl_masuk": start, "tgl_keluar": None,
            "segmen_tujuan": None, "jeda_hari": None, "alasan_keluar": None,
            "tahun_lahir": int(start.year - np.clip(rng.normal(30, 8), 18, 58)),
            "jenis_kelamin": rng.choice(["L", "P"]),
        }
        active[wid] = [rec, w, at]

    def leave(wid: str, when: date, reason: str, dest_p):
        rec = active[wid][0]
        rec["tgl_keluar"] = when
        rec["alasan_keluar"] = reason
        dest = rng.choice(["PBPU", "NONAKTIF", "PPU_LAIN"], p=dest_p)
        rec["segmen_tujuan"] = dest
        if dest == "PBPU":
            rec["jeda_hari"] = int(rng.integers(0, 61)) if reason == "phk" else int(rng.integers(0, 181))
        elif dest == "PPU_LAIN":
            rec["jeda_hari"] = int(rng.integers(0, 61))

    y0 = years[0]
    floor_start = date(founded, 1, 1)
    for _ in range(n0):
        if founded >= y0:
            start = _rand_date(rng, y0, 1, 3)
        else:
            start = date(y0, 1, 1) - timedelta(days=int(rng.exponential(365 * 4)) + 1)
            start = max(start, floor_start)
        hire(start, y0)

    layoff = None
    if archetype == "phk_massal_sah" and len(years) > 1:
        layoff = (int(rng.choice(years[1:])), int(rng.integers(1, 12)), rng.uniform(0.3, 0.5))

    target = n0
    lo_hi = {"mikro": (1, 6), "kecil": (3, 25)}.get(e.skala_usaha)
    finished: list[dict] = []
    natural_dest = [0.12, 0.40, 0.48]

    for y in years:
        u = umk_map[(e.kode_wilayah, y)]
        if uniform_wage is not None and y > y0:
            uniform_wage = max(_round_k(uniform_wage * (1 + rng.normal(0.04, 0.01))), u)

        # 1) penyesuaian upah tahunan untuk pekerja lama
        for wid, st in active.items():
            rec, w, at = st
            if rec["tgl_masuk"].year >= y:
                continue
            if uniform_wage is not None:
                w = uniform_wage
            elif archetype == "umkm_bawah_umk":
                w = max(_round_k(w * (1 + max(0, rng.normal(sec.kenaikan_merit, 0.02)))),
                        _round_k(u * LANTAI_UPAH_UMKM_RASIO))
            elif at:
                if rng.random() < promo:
                    w, at = _round_k(u * rng.uniform(1.03, 1.2)), False
                else:
                    w = u
            else:
                w = _round_k(w * (1 + max(0, rng.normal(sec.kenaikan_merit, 0.025))))
                if umkm:
                    w = max(w, _round_k(u * LANTAI_UPAH_UMKM_RASIO))
                elif w <= u:
                    w, at = u, True
            st[1], st[2] = w, at

        # 2) PHK massal yang sah
        if layoff and layoff[0] == y:
            _, month, frac = layoff
            pool = [wid for wid, st in active.items() if st[0]["tgl_masuk"] < date(y, month, 1)]
            k = int(round(len(pool) * frac))
            for wid in rng.choice(pool, size=k, replace=False):
                leave(wid, _rand_date(rng, y, month, min(12, month + 1)), "phk", [0.45, 0.35, 0.20])
            target = len(active) - k

        # 3) turnover alami
        for wid, st in active.items():
            rec = st[0]
            if rec["tgl_keluar"] is None and rec["tgl_masuk"].year < y and rng.random() < sec.turnover:
                reason = rng.choice(["resign", "kontrak_habis", "phk"], p=[0.55, 0.35, 0.10])
                leave(wid, _rand_date(rng, y), reason, natural_dest)

        # 4) rekrutmen menuju target headcount
        if y > y0:
            g = rng.normal(0.0, 0.03) if layoff and y >= layoff[0] else np.clip(rng.normal(0.02, 0.07), -0.3, 0.4)
            target = max(1, int(round(target * (1 + g))))
            if lo_hi:
                target = int(np.clip(target, *lo_hi))
        staying = sum(1 for st in active.values() if st[0]["tgl_keluar"] is None)
        for _ in range(max(0, target - staying)):
            hire(_rand_date(rng, y), y)

        # 5) catat upah tahun ini, lalu buang pekerja yang sudah keluar
        for wid, st in active.items():
            rec, w, _ = st
            m = _months_active(rec["tgl_masuk"], rec["tgl_keluar"], y)
            if m > 0:
                wage_rows.append((wid, e.employer_id, y, int(w), m))
        gone = [wid for wid, st in active.items() if st[0]["tgl_keluar"] is not None]
        for wid in gone:
            finished.append(active.pop(wid)[0])

    for rec in finished + [st[0] for st in active.values()]:
        worker_rows.append(tuple(rec.values()))
