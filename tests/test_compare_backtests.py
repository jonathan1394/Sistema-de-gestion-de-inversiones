import json

from scripts.compare_backtests import (
    _apply_filters,
    _compute_weighted_scores,
    _resolve_files,
    export_ranking_csv,
    export_ranking_json,
    load_snapshot,
    print_ranking,
)


def _write_metrics(path, *, sharpe, drawdown, profit_factor, roi, win_rate, trades):
    payload = {
        "metrics": {
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": drawdown,
            "profit_factor": profit_factor,
            "roi_pct": roi,
            "win_rate": win_rate,
            "total_trades": trades,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_snapshot_reads_expected_fields(tmp_path):
    metrics_file = tmp_path / "metrics.json"
    _write_metrics(
        metrics_file,
        sharpe=1.2,
        drawdown=-12.5,
        profit_factor=1.9,
        roi=14.2,
        win_rate=53.0,
        trades=87,
    )

    snap = load_snapshot(str(metrics_file), "B1")

    assert snap.name == "B1"
    assert snap.sharpe_ratio == 1.2
    assert snap.max_drawdown_pct == -12.5
    assert snap.profit_factor == 1.9
    assert snap.total_trades == 87


def test_apply_filters_excludes_low_quality_runs(tmp_path):
    m1 = tmp_path / "m1.json"
    m2 = tmp_path / "m2.json"
    _write_metrics(m1, sharpe=1.3, drawdown=-10, profit_factor=1.6, roi=10, win_rate=51, trades=80)
    _write_metrics(m2, sharpe=0.7, drawdown=-8, profit_factor=1.2, roi=7, win_rate=48, trades=30)

    snapshots = [load_snapshot(str(m1), "B1"), load_snapshot(str(m2), "B2")]
    kept, excluded = _apply_filters(snapshots, min_trades=50, min_sharpe=1.0)

    assert [s.name for s in kept] == ["B1"]
    assert [s.name for s in excluded] == ["B2"]


def test_weighted_scores_prioritize_sharpe_and_drawdown(tmp_path):
    m1 = tmp_path / "m1.json"
    m2 = tmp_path / "m2.json"
    m3 = tmp_path / "m3.json"
    _write_metrics(m1, sharpe=1.8, drawdown=-20, profit_factor=1.1, roi=9, win_rate=45, trades=90)
    _write_metrics(m2, sharpe=1.1, drawdown=-6, profit_factor=1.5, roi=8, win_rate=55, trades=95)
    _write_metrics(m3, sharpe=0.9, drawdown=-4, profit_factor=2.0, roi=11, win_rate=60, trades=100)

    snaps = [load_snapshot(str(m1), "B1"), load_snapshot(str(m2), "B2"), load_snapshot(str(m3), "B3")]
    scores = _compute_weighted_scores(snaps, w_sharpe=2.0, w_drawdown=2.0, w_profit_factor=1.0)

    assert len(scores) == 3
    assert max(scores) == scores[2]


def test_export_ranking_json_and_csv(tmp_path):
    m1 = tmp_path / "m1.json"
    m2 = tmp_path / "m2.json"
    _write_metrics(m1, sharpe=1.3, drawdown=-9, profit_factor=1.7, roi=12, win_rate=52, trades=70)
    _write_metrics(m2, sharpe=0.8, drawdown=-5, profit_factor=1.1, roi=5, win_rate=47, trades=65)

    snaps = [load_snapshot(str(m1), "B1"), load_snapshot(str(m2), "B2")]
    scores = _compute_weighted_scores(snaps, w_sharpe=1.0, w_drawdown=1.0, w_profit_factor=1.0)
    ranked = print_ranking(snaps, scores, w_sharpe=1.0, w_drawdown=1.0, w_profit_factor=1.0)

    json_path = export_ranking_json(ranked, str(tmp_path / "rank.json"))
    csv_path = export_ranking_csv(ranked, str(tmp_path / "rank.csv"))

    exported = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(exported) == 2
    assert exported[0]["rank"] == 1
    assert csv_path.exists()


def test_resolve_files_accepts_legacy_and_new_modes():
    class Args:
        files = ["one.json", "two.json"]
        a = None
        b = None

    assert _resolve_files(Args) == ["one.json", "two.json"]

    class LegacyArgs:
        files = None
        a = "a.json"
        b = "b.json"

    assert _resolve_files(LegacyArgs) == ["a.json", "b.json"]
