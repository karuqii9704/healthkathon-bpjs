"""Tahap 2: penyisipan pelanggaran secara blind.

Dijalankan oleh anggota tim yang TIDAK membangun model, dengan seed rahasia.
Output-nya adalah versi "yang dilaporkan ke BPJS" plus label kebenaran.

Modus (dan sub-modus mudah / sulit):
- upah      : lapor_umk (mudah), upah_beku (mudah), potong_sebagian (sulit)
- headcount : daftar_sebagian — 35–60% terdaftar (mudah) / 75–90% (sulit)
- status    : pindah_pbpu — 25–50% dalam 1 bulan (mudah) / 8–18% tersebar 2–4 bulan (sulit)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .calculator import iuran_ppu
from .config import PLAFON_UPAH_IURAN, Config
from .world import World, _months_active

_MODE_ORDER = ["headcount", "status", "upah"]  # sembunyikan dulu, baru pindahkan, baru potong upah


@dataclass
class Injected:
    workers: pd.DataFrame         # pekerja yang tercatat di BPJS (dilaporkan)
    wages: pd.DataFrame           # riwayat upah dilaporkan
    labels: pd.DataFrame          # label per badan usaha (rahasia)
    hidden_workers: pd.DataFrame  # pekerja riil yang tidak didaftarkan (rahasia)
    moved_workers: pd.DataFrame   # pekerja yang dipindah ke PBPU padahal masih bekerja (rahasia)
    true_wages: pd.DataFrame      # upah riil seluruh pekerja (rahasia, untuk uji kalkulator)


class _Injector:
    def __init__(self, world: World, cfg: Config, rng):
        self.cfg, self.rng = cfg, rng
        self.years = list(cfg.years)
        region = world.employers.set_index("employer_id").kode_wilayah
        umk = world.umk.set_index(["kode_wilayah", "tahun"]).umk

        w = world.wages.copy()
        w["umk"] = umk.reindex(list(zip(w.employer_id.map(region), w.tahun))).to_numpy()
        w["upah_dilaporkan"] = w.upah_riil
        w["bulan_dilaporkan"] = w.bulan_aktif
        w["_drop"] = False
        self.w = w
        self.k = world.workers.copy()
        self.w_idx = w.groupby("employer_id").indices
        self.k_idx = self.k.groupby("employer_id").indices
        self.hidden: set[str] = set()
        self.moved: list[dict] = []

    # --- modus upah -----------------------------------------------------
    def upah(self, eid: str, hard: bool):
        w, rng = self.w, self.rng
        rows = self.w_idx.get(eid, np.array([], dtype=int))
        rows = rows[~w._drop.to_numpy()[rows]]
        if len(rows) == 0:
            return None
        sub = w.loc[rows]
        if not hard:
            if rng.random() < 0.5:
                new = np.where(sub.upah_riil > sub.umk, sub.umk, sub.upah_riil)
                name = "lapor_umk"
            else:
                first = sub.sort_values("tahun").groupby("worker_id").upah_riil.transform("first")
                new = np.minimum(first.reindex(sub.index), sub.upah_riil)
                name = "upah_beku"
        else:
            ratio = (sub.upah_riil / sub.umk).groupby(sub.worker_id).mean()
            cand = ratio[ratio > 1.25].index
            if len(cand) == 0:
                cand = ratio[ratio > 1.05].index
            if len(cand) == 0:
                return None
            k = max(1, int(round(len(cand) * rng.uniform(0.5, 1.0))))
            pick = rng.choice(cand, size=k, replace=False)
            factor = pd.Series(rng.uniform(0.6, 0.85, size=k), index=pick)
            f = sub.worker_id.map(factor).fillna(1.0)
            cut = np.round(sub.upah_riil * f / 50_000) * 50_000
            new = np.minimum(sub.upah_riil, np.maximum(sub.umk, cut))
            name = "potong_sebagian"
        new = np.asarray(new, dtype=np.int64)
        # harus benar-benar mengurangi iuran (upah di atas plafon tidak berpengaruh)
        if not (np.minimum(new, PLAFON_UPAH_IURAN) < np.minimum(sub.upah_riil, PLAFON_UPAH_IURAN)).any():
            return None
        w.loc[rows, "upah_dilaporkan"] = new
        return name

    # --- modus headcount ------------------------------------------------
    def headcount(self, eid: str, hard: bool):
        k, rng = self.k, self.rng
        idx = self.k_idx[eid]
        if len(idx) < 2:
            return None
        reg = rng.uniform(0.75, 0.9) if hard else rng.uniform(0.35, 0.6)
        n_hide = int(np.clip(round(len(idx) * (1 - reg)), 1, len(idx) - 1))
        # pekerja baru (kontrak) lebih sering tidak didaftarkan
        order = k.loc[idx, "tgl_masuk"].rank(method="first").to_numpy()
        p = order / order.sum()
        hide = k.loc[rng.choice(idx, size=n_hide, replace=False, p=p), "worker_id"]
        self.hidden.update(hide)
        rows = self.w_idx.get(eid, np.array([], dtype=int))
        self.w.loc[rows[self.w.loc[rows, "worker_id"].isin(hide).to_numpy()], "_drop"] = True
        return "daftar_sebagian"

    # --- modus status ---------------------------------------------------
    def status(self, eid: str, hard: bool):
        k, rng = self.k, self.rng
        y = int(rng.choice(self.years[1:]))
        m = int(rng.integers(1, 9))  # sisakan bulan setelah pindah agar kerugian terlihat
        d = date(y, m, 1)
        idx = self.k_idx[eid]
        sub = k.loc[idx]
        alive = (sub.tgl_masuk < d) & sub.tgl_keluar.apply(lambda t: t is None or t > d + timedelta(days=120))
        alive &= ~sub.worker_id.isin(self.hidden)
        pool = sub.index[alive.to_numpy()]
        if len(pool) < (12 if hard else 5):
            return None
        frac = rng.uniform(0.08, 0.18) if hard else rng.uniform(0.25, 0.5)
        n_move = max(2, int(round(len(pool) * frac)))
        span = int(rng.integers(2, 5)) if hard else 1
        for i in rng.choice(pool, size=n_move, replace=False):
            mm = min(12, m + int(rng.integers(0, span)))
            when = date(y, mm, int(rng.integers(1, 29)))
            rec = k.loc[i]
            self.moved.append({"worker_id": rec.worker_id, "employer_id": eid, "tgl_pindah": when,
                               "tgl_keluar_riil": rec.tgl_keluar})
            k.at[i, "tgl_keluar"] = when
            k.at[i, "segmen_tujuan"] = "PBPU"
            k.at[i, "jeda_hari"] = int(rng.integers(0, 31 if hard else 8))
            k.at[i, "alasan_keluar"] = "resign"
            rows = self.w_idx[eid]
            rows = rows[(self.w.loc[rows, "worker_id"] == rec.worker_id).to_numpy()]
            for r in rows:
                t = int(self.w.at[r, "tahun"])
                if t > y:
                    self.w.at[r, "_drop"] = True
                elif t == y:
                    self.w.at[r, "bulan_dilaporkan"] = _months_active(rec.tgl_masuk, when, y)
        return "pindah_pbpu"


def inject(world: World, cfg: Config) -> Injected:
    rng = np.random.default_rng(cfg.inject_seed)
    inj = _Injector(world, cfg, rng)
    emp_ids = world.employers.employer_id.to_numpy()
    n_target = int(round(len(emp_ids) * cfg.violation_rate))
    candidates = rng.permutation(emp_ids)

    modes = list(cfg.mode_weights)
    mp = np.array(list(cfg.mode_weights.values()))
    mp = mp / mp.sum()
    records = {}
    for eid in candidates:
        if len(records) >= n_target:
            break
        n_modes = 2 if rng.random() < cfg.p_two_modes else 1
        wanted = list(rng.choice(modes, size=n_modes, replace=False, p=mp))
        applied = []
        for mode in sorted(wanted, key=_MODE_ORDER.index):
            hard = rng.random() >= cfg.p_easy
            name = getattr(inj, mode)(eid, hard)
            if name:
                applied.append((name, hard))
        # fallback: usaha terlalu kecil untuk modus terpilih -> coba modus lain
        for mode in _MODE_ORDER:
            if applied:
                break
            name = getattr(inj, mode)(eid, False)
            if name:
                applied.append((name, False))
        # tidak ada modus yang bisa diterapkan (mis. usaha mikro 1 pekerja di bawah UMK) -> ganti kandidat
        if applied:
            records[eid] = applied

    w, k = inj.w, inj.k
    hidden_mask = k.worker_id.isin(inj.hidden)
    hidden_workers = k.loc[hidden_mask, ["worker_id", "employer_id", "tgl_masuk", "tgl_keluar"]].reset_index(drop=True)
    moved = pd.DataFrame(inj.moved, columns=["worker_id", "employer_id", "tgl_pindah", "tgl_keluar_riil"])

    reported_wages = w.loc[~w._drop, ["worker_id", "employer_id", "tahun", "upah_dilaporkan", "bulan_dilaporkan"]]
    reported_wages = reported_wages.rename(columns={"bulan_dilaporkan": "bulan_aktif"}).reset_index(drop=True)
    reported_workers = k.loc[~hidden_mask].reset_index(drop=True)

    labels = _build_labels(world, cfg, inj, records, reported_wages)
    return Injected(reported_workers, reported_wages, labels, hidden_workers, moved, world.wages.copy())


def _build_labels(world, cfg, inj, records, reported_wages) -> pd.DataFrame:
    last = max(cfg.years)
    truth = world.wages.assign(iuran=iuran_ppu(world.wages.upah_riil, world.wages.bulan_aktif))
    rep = reported_wages.assign(iuran=iuran_ppu(reported_wages.upah_dilaporkan, reported_wages.bulan_aktif))
    t_tot = truth.groupby("employer_id").iuran.sum()
    r_tot = rep.groupby("employer_id").iuran.sum()
    t_last = truth[truth.tahun == last].groupby("employer_id").iuran.sum()
    r_last = rep[rep.tahun == last].groupby("employer_id").iuran.sum()

    cut = inj.w[(inj.w.upah_dilaporkan < inj.w.upah_riil) & ~inj.w._drop]
    n_cut = cut.groupby("employer_id").worker_id.nunique()
    n_hidden = pd.Series(list(inj.hidden), dtype=object).map(
        inj.k.set_index("worker_id").employer_id).value_counts()
    n_moved = pd.Series([m["employer_id"] for m in inj.moved], dtype=object).value_counts()

    lab = world.employers[["employer_id"]].copy()
    lab = lab.merge(world.archetypes, on="employer_id", how="left")
    lab["is_violator"] = lab.employer_id.isin(records).astype(int)
    lab["modus"] = lab.employer_id.map(lambda e: "|".join(n for n, _ in records.get(e, [])) or None)
    lab["kesulitan"] = [
        ("mudah" if any(not h for _, h in records[e]) else "sulit") if e in records
        else ("hard_negative" if isinstance(t, str) else "normal")
        for e, t in zip(lab.employer_id, lab.hard_negative_type)
    ]
    lab["pekerja_tersembunyi"] = lab.employer_id.map(n_hidden).fillna(0).astype(int)
    lab["pekerja_dipindah_pbpu"] = lab.employer_id.map(n_moved).fillna(0).astype(int)
    lab["pekerja_upah_dikurangi"] = lab.employer_id.map(n_cut).fillna(0).astype(int)
    lab["iuran_tak_tertagih_tahun_terakhir"] = (
        lab.employer_id.map(t_last).fillna(0) - lab.employer_id.map(r_last).fillna(0)).round().astype(np.int64)
    lab["iuran_tak_tertagih_total"] = (
        lab.employer_id.map(t_tot).fillna(0) - lab.employer_id.map(r_tot).fillna(0)).round().astype(np.int64)
    return lab
