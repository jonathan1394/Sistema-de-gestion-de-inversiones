from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BacktestSnapshot:
    name: str
    path: Path
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    roi_pct: float
    win_rate: float
    total_trades: int


@dataclass
class RankedSnapshot:
    rank: int
    score: float
    snapshot: BacktestSnapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare backtest metrics.json files")
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="List of metrics.json files to compare (2 or more)",
    )
    parser.add_argument("--a", default=None, help="Path to first metrics.json (legacy mode)")
    parser.add_argument("--b", default=None, help="Path to second metrics.json (legacy mode)")
    parser.add_argument("--w-sharpe", type=float, default=1.0, help="Weight for Sharpe")
    parser.add_argument("--w-drawdown", type=float, default=1.0, help="Weight for Drawdown")
    parser.add_argument("--w-profit-factor", type=float, default=1.0, help="Weight for Profit Factor")
    parser.add_argument("--min-trades", type=int, default=0, help="Minimum trade count filter")
    parser.add_argument("--min-sharpe", type=float, default=float("-inf"), help="Minimum Sharpe filter")
    parser.add_argument("--export-json", default=None, help="Export ranking to JSON file")
    parser.add_argument("--export-csv", default=None, help="Export ranking to CSV file")
    return parser.parse_args()


def load_snapshot(path_value: str, name: str) -> BacktestSnapshot:
    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})

    return BacktestSnapshot(
        name=name,
        path=path,
        sharpe_ratio=float(metrics.get("sharpe_ratio", 0.0)),
        max_drawdown_pct=float(metrics.get("max_drawdown_pct", 0.0)),
        profit_factor=float(metrics.get("profit_factor", 0.0)),
        roi_pct=float(metrics.get("roi_pct", 0.0)),
        win_rate=float(metrics.get("win_rate", 0.0)),
        total_trades=int(metrics.get("total_trades", 0)),
    )


def _resolve_files(args: argparse.Namespace) -> list[str]:
    if args.files:
        if len(args.files) < 2:
            raise ValueError("--files requires at least 2 paths")
        return args.files
    if args.a and args.b:
        return [args.a, args.b]
    raise ValueError("Use --files path1 path2 [path3 ...] or provide --a and --b")


def _rank_desc(values: list[float]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    rank = [0] * len(values)
    for index, original_idx in enumerate(order):
        rank[original_idx] = index + 1
    return rank


def _rank_asc(values: list[float]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    rank = [0] * len(values)
    for index, original_idx in enumerate(order):
        rank[original_idx] = index + 1
    return rank


def _compute_weighted_scores(
    snapshots: list[BacktestSnapshot],
    w_sharpe: float,
    w_drawdown: float,
    w_profit_factor: float,
) -> list[float]:
    sharpe = [s.sharpe_ratio for s in snapshots]
    drawdown_abs = [abs(s.max_drawdown_pct) for s in snapshots]
    profit_factor = [s.profit_factor for s in snapshots]

    rank_sharpe = _rank_desc(sharpe)
    rank_drawdown = _rank_asc(drawdown_abs)
    rank_pf = _rank_desc(profit_factor)

    n = len(snapshots)
    scores: list[float] = []
    for i in range(n):
        points_sharpe = (n - rank_sharpe[i] + 1) * w_sharpe
        points_drawdown = (n - rank_drawdown[i] + 1) * w_drawdown
        points_pf = (n - rank_pf[i] + 1) * w_profit_factor
        scores.append(points_sharpe + points_drawdown + points_pf)
    return scores


def _apply_filters(
    snapshots: list[BacktestSnapshot],
    min_trades: int,
    min_sharpe: float,
) -> tuple[list[BacktestSnapshot], list[BacktestSnapshot]]:
    kept: list[BacktestSnapshot] = []
    excluded: list[BacktestSnapshot] = []
    for snap in snapshots:
        if snap.total_trades < min_trades or snap.sharpe_ratio < min_sharpe:
            excluded.append(snap)
        else:
            kept.append(snap)
    return kept, excluded


def print_table(snapshots: list[BacktestSnapshot]) -> None:
    print("Metric               Name    Value")
    print("-" * 64)
    for snap in snapshots:
        print(f"Sharpe ratio         {snap.name:<6}  {snap.sharpe_ratio:>10.3f}")
        print(f"Max drawdown %       {snap.name:<6}  {snap.max_drawdown_pct:>10.2f}")
        print(f"Profit factor        {snap.name:<6}  {snap.profit_factor:>10.3f}")
        print(f"ROI %                {snap.name:<6}  {snap.roi_pct:>10.2f}")
        print(f"Win rate %           {snap.name:<6}  {snap.win_rate:>10.2f}")
        print(f"Total trades         {snap.name:<6}  {snap.total_trades:>10d}")
        print("-" * 64)


def print_ranking(
    snapshots: list[BacktestSnapshot],
    scores: list[float],
    w_sharpe: float,
    w_drawdown: float,
    w_profit_factor: float,
) -> list[RankedSnapshot]:
    ranked_pairs = sorted(zip(snapshots, scores), key=lambda pair: pair[1], reverse=True)
    ranked: list[RankedSnapshot] = [
        RankedSnapshot(rank=idx, score=score, snapshot=snap)
        for idx, (snap, score) in enumerate(ranked_pairs, start=1)
    ]
    print("Weighted ranking:")
    print(
        f"(weights: sharpe={w_sharpe}, drawdown={w_drawdown}, profit_factor={w_profit_factor})"
    )
    for row in ranked:
        print(f"{row.rank}. {row.snapshot.name}  score={row.score:.2f}  file={row.snapshot.path}")
    return ranked


def export_ranking_json(ranked: list[RankedSnapshot], output_path: str) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "rank": row.rank,
            "score": row.score,
            "name": row.snapshot.name,
            "path": str(row.snapshot.path),
            "sharpe_ratio": row.snapshot.sharpe_ratio,
            "max_drawdown_pct": row.snapshot.max_drawdown_pct,
            "profit_factor": row.snapshot.profit_factor,
            "roi_pct": row.snapshot.roi_pct,
            "win_rate": row.snapshot.win_rate,
            "total_trades": row.snapshot.total_trades,
        }
        for row in ranked
    ]
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def export_ranking_csv(ranked: list[RankedSnapshot], output_path: str) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rank",
                "score",
                "name",
                "path",
                "sharpe_ratio",
                "max_drawdown_pct",
                "profit_factor",
                "roi_pct",
                "win_rate",
                "total_trades",
            ],
        )
        writer.writeheader()
        for row in ranked:
            writer.writerow(
                {
                    "rank": row.rank,
                    "score": row.score,
                    "name": row.snapshot.name,
                    "path": str(row.snapshot.path),
                    "sharpe_ratio": row.snapshot.sharpe_ratio,
                    "max_drawdown_pct": row.snapshot.max_drawdown_pct,
                    "profit_factor": row.snapshot.profit_factor,
                    "roi_pct": row.snapshot.roi_pct,
                    "win_rate": row.snapshot.win_rate,
                    "total_trades": row.snapshot.total_trades,
                }
            )
    return destination


def main() -> None:
    args = parse_args()
    files = _resolve_files(args)

    all_snapshots = [load_snapshot(path, f"B{i + 1}") for i, path in enumerate(files)]
    snapshots, excluded = _apply_filters(
        snapshots=all_snapshots,
        min_trades=args.min_trades,
        min_sharpe=args.min_sharpe,
    )

    if len(snapshots) < 2:
        raise RuntimeError("Not enough backtests after filters. Need at least 2.")

    print("=" * 72)
    print("BACKTEST COMPARISON")
    print("=" * 72)
    for snap in all_snapshots:
        print(f"{snap.name}: {snap.path}")
    print("")

    if excluded:
        print("Excluded by filters:")
        for snap in excluded:
            print(
                f"- {snap.name} (trades={snap.total_trades}, sharpe={snap.sharpe_ratio:.3f})"
            )
        print("")

    print_table(snapshots)
    print("")

    scores = _compute_weighted_scores(
        snapshots=snapshots,
        w_sharpe=args.w_sharpe,
        w_drawdown=args.w_drawdown,
        w_profit_factor=args.w_profit_factor,
    )
    ranked = print_ranking(
        snapshots=snapshots,
        scores=scores,
        w_sharpe=args.w_sharpe,
        w_drawdown=args.w_drawdown,
        w_profit_factor=args.w_profit_factor,
    )

    if args.export_json:
        json_path = export_ranking_json(ranked, args.export_json)
        print(f"\nExported JSON: {json_path}")
    if args.export_csv:
        csv_path = export_ranking_csv(ranked, args.export_csv)
        print(f"Exported CSV: {csv_path}")


if __name__ == "__main__":
    main()
