import pytest

from generator.calculator import estimasi_iuran_tak_tertagih, iuran_ppu
from generator.config import PLAFON_UPAH_IURAN, Config
from generator.export import write_all
from generator.inject import inject
from generator.validate import validate
from generator.world import build_world


@pytest.fixture(scope="module")
def small():
    cfg = Config(n_employers=200, seed=1, inject_seed=2)
    world = build_world(cfg)
    return cfg, world, inject(world, cfg)


def test_prevalence_exact(small):
    cfg, _, inj = small
    assert inj.labels.is_violator.sum() == round(cfg.n_employers * cfg.violation_rate)


def test_deterministic():
    cfg = Config(n_employers=50, seed=3, inject_seed=4)
    a, b = inject(build_world(cfg), cfg), inject(build_world(cfg), cfg)
    assert a.labels.equals(b.labels)
    assert a.wages.equals(b.wages)


def test_inject_seed_changes_violators_not_world():
    w = build_world(Config(n_employers=100, seed=5))
    a = inject(w, Config(n_employers=100, seed=5, inject_seed=1)).labels
    b = inject(w, Config(n_employers=100, seed=5, inject_seed=2)).labels
    assert not a.is_violator.equals(b.is_violator)


def test_compliant_unchanged_and_violators_lose(small):
    _, _, inj = small
    lab = inj.labels
    assert (lab.loc[lab.is_violator == 0, "iuran_tak_tertagih_total"] == 0).all()
    assert (lab.loc[lab.is_violator == 1, "iuran_tak_tertagih_total"] > 0).all()


def test_hard_negatives_present(small):
    _, _, inj = small
    assert (inj.labels.kesulitan == "hard_negative").sum() > 0


def test_calculator_respects_plafon():
    assert iuran_ppu(PLAFON_UPAH_IURAN * 2, 1) == iuran_ppu(PLAFON_UPAH_IURAN, 1)
    est = estimasi_iuran_tak_tertagih(upah_wajar=6_000_000, upah_dilaporkan=5_000_000, jumlah_pekerja=10)
    assert est == pytest.approx(1_000_000 * 0.05 * 10 * 12)
    assert estimasi_iuran_tak_tertagih(20_000_000, 15_000_000, 10) == 0


def test_validation_passes(small, tmp_path):
    cfg, world, inj = small
    write_all(world, inj, cfg, tmp_path)
    report, ok = validate(tmp_path)
    assert ok, report
    assert not (tmp_path / "manifest.json").read_text(encoding="utf-8").count("inject_seed")
