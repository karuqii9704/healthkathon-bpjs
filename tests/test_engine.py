import shutil

import pytest

from engine import features, score
from engine.evaluate import evaluate
from generator.config import Config
from generator.export import write_all
from generator.inject import inject
from generator.world import build_world


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    cfg = Config(n_employers=400, seed=11, inject_seed=12)
    world = build_world(cfg)
    write_all(world, inject(world, cfg), cfg, out)
    return out


def test_engine_runs_without_labels(dataset, tmp_path):
    blind = tmp_path / "blind"
    shutil.copytree(dataset, blind, ignore=shutil.ignore_patterns("label"))
    res, S = score.run(features.build(features.load(blind)))
    assert len(res) == 400
    assert res.skor.between(0, 100).all()
    assert set(res.keyakinan) <= {"tinggi", "sedang", "rendah"}


def test_top_has_reasons_and_estimate(dataset):
    res, _ = score.run(features.build(features.load(dataset)))
    top = res.head(20)
    assert (top.alasan.str.len() > 0).all()
    assert (top.estimasi_iuran_tak_tertagih >= 0).all()


def test_beats_random(dataset):
    res, _ = score.run(features.build(features.load(dataset)))
    m = evaluate(res, dataset)
    assert m["lift"] > 2.5
    assert m["salah_tandai_umkm"] <= 0.05
