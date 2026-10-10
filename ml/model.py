"""Model peluang pelanggaran, kalibrasi, atribusi fitur, dan ekspor ke JSON untuk browser.

Model sengaja hanya memakai fitur mentah (bukan skor aturan / anomali), supaya menjadi second opinion
yang independen dari mesin aturan. Label hanya berasal dari badan usaha yang sudah diperiksa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

# (kolom, label tampilan, monotonic constraint: +1 naik = lebih berisiko, -1 turun = lebih berisiko, 0 bebas)
FEATURES = [
    ("porsi_tepat_umk", "Porsi pekerja tepat di UMK", 0),
    ("porsi_bawah_umk", "Porsi pekerja di bawah UMK", 0),
    ("porsi_atas_umk", "Porsi pekerja di atas UMK", 0),
    ("median_rasio_umk", "Median upah / UMK", 0),
    ("p90_rasio_umk", "Upah P90 / UMK", 0),
    ("porsi_upah_modus", "Porsi upah seragam", 0),
    ("rasio_benchmark", "Upah vs benchmark sektor", -1),
    ("porsi_upah_beku", "Porsi upah tidak naik", 1),
    ("porsi_naik_sama_umk", "Porsi kenaikan = kenaikan UMK", 0),
    ("rasio_headcount_oss", "Pekerja terdaftar / rencana OSS", -1),
    ("klaster_pbpu_n", "Pekerja pindah PPU→PBPU (klaster)", 1),
    ("klaster_pbpu_porsi", "Porsi pekerja pindah ke PBPU", 1),
    ("n_pekerja", "Pekerja dilaporkan", 0),
    ("tk_oss", "Rencana tenaga kerja OSS", 0),
    ("tahun_teramati", "Tahun data teramati", 0),
    ("skala", "Skala usaha (0 mikro … 3 besar)", 0),
    ("padat_karya", "Sektor padat karya", 0),
]
COLS = [c for c, _, _ in FEATURES]
LABELS = {c: l for c, l, _ in FEATURES}

PARAMS = dict(max_iter=250, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=12,
              l2_regularization=1.0, early_stopping=False)


def matrix(fitur: pd.DataFrame) -> pd.DataFrame:
    X = fitur.copy()
    X["skala"] = X.skala_usaha.map({"mikro": 0, "kecil": 1, "menengah": 2, "besar": 3})
    X["padat_karya"] = X.padat_karya.astype(str).str.lower().eq("true").astype(int)
    return X[COLS].astype(float)


def fit(X: pd.DataFrame, y: pd.Series, w: pd.Series | None = None, seed: int = 0) -> HistGradientBoostingClassifier:
    clf = HistGradientBoostingClassifier(monotonic_cst=[m for _, _, m in FEATURES], random_state=seed, **PARAMS)
    clf.fit(X, y, sample_weight=None if w is None else w.to_numpy())
    return clf


def calibrator(p_raw: np.ndarray, y: np.ndarray, w: np.ndarray | None = None) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)  # tidak pernah klaim kepastian mutlak
    iso.fit(p_raw, y, sample_weight=w)
    return iso


# ---------------------------------------------------------------- ekspor + atribusi (Saabas, aditif persis)

def _trees(clf) -> list[dict]:
    out = []
    for (pred,) in clf._predictors:
        n = pred.nodes
        val = n["value"].astype(float).copy()
        cnt = n["count"].astype(float)

        def mean(i: int) -> float:  # nilai harapan node = rata-rata leaf berbobot jumlah sampel
            if n["is_leaf"][i]:
                return val[i]
            l, r = int(n["left"][i]), int(n["right"][i])
            val[i] = (mean(l) * cnt[l] + mean(r) * cnt[r]) / (cnt[l] + cnt[r])
            return val[i]

        mean(0)
        out.append({
            "f": n["feature_idx"].astype(int).tolist(),
            "t": [float(x) for x in n["num_threshold"]],
            "m": n["missing_go_to_left"].astype(int).tolist(),
            "l": n["left"].astype(int).tolist(), "r": n["right"].astype(int).tolist(),
            "leaf": n["is_leaf"].astype(int).tolist(),
            "v": [float(f"{x:.6g}") for x in val],
        })
    return out


def export(clf, iso: IsotonicRegression, X_ref: pd.DataFrame) -> dict:
    """Model sebagai JSON: dievaluasi di browser oleh dashboard (lihat payrayModel di template.html)."""
    return {
        "fitur": COLS, "label": [LABELS[c] for c in COLS],
        "monoton": [m for _, _, m in FEATURES],
        "base": float(clf._baseline_prediction.ravel()[0]),
        "trees": _trees(clf),
        "kalibrasi": {"x": [round(float(x), 5) for x in iso.X_thresholds_],
                      "y": [round(float(y), 5) for y in iso.y_thresholds_]},
        "rentang": {c: [float(np.nanquantile(X_ref[c], q)) for q in (0.01, 0.5, 0.99)] for c in COLS},
    }


def contributions(model: dict, x: np.ndarray) -> tuple[float, np.ndarray]:
    """Versi Python dari evaluator browser: (log-odds, kontribusi per fitur). Dipakai untuk uji kesamaan."""
    phi = np.zeros(len(model["fitur"]))
    raw = model["base"]
    for t in model["trees"]:
        i = 0
        raw += t["v"][0]
        while not t["leaf"][i]:
            f = t["f"][i]
            xv = x[f]
            j = t["l"][i] if (t["m"][i] if np.isnan(xv) else xv <= t["t"][i]) else t["r"][i]
            phi[f] += t["v"][j] - t["v"][i]
            i = j
    return raw + phi.sum(), phi


def calibrate(model: dict, p_raw: np.ndarray) -> np.ndarray:
    return np.interp(p_raw, model["kalibrasi"]["x"], model["kalibrasi"]["y"])
