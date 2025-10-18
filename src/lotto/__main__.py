"""Command line interface for the lotto toolkit."""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .analyze import compute_metrics, render_report, save_metrics, save_report
from .exceptions import FetchError, NormalizationError
from .fetchers import five_hundred, official
from .generate import generate_from_file, save_picks
from .normalize import load_draws, normalise_draws, save_draws

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger("lotto")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 1
    try:
        return args.handler(args)
    except FetchError as exc:
        LOGGER.error("数据抓取失败：%s", exc)
        return 2
    except NormalizationError as exc:
        LOGGER.error("数据格式错误：%s", exc)
        return 3
    except FileNotFoundError as exc:
        LOGGER.error(str(exc))
        return 4


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lotto", description="双色球历史数据抓取与分析工具")
    parser.add_argument("--version", action="version", version=f"lotto {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    fetch_parser = subparsers.add_parser("fetch", help="抓取历史开奖数据")
    fetch_parser.add_argument("--years", type=int, default=15, help="抓取年份跨度，默认15年")
    fetch_parser.add_argument(
        "--source",
        choices=("official", "500"),
        default="official",
        help="数据来源，默认官方，若失败自动回退至500.com",
    )
    fetch_parser.add_argument("--out", default="data/draws.csv", help="输出CSV路径")
    fetch_parser.add_argument("--sleep", type=float, default=0.5, help="请求间隔秒数，默认0.5s")
    fetch_parser.set_defaults(handler=_handle_fetch)

    analyze_parser = subparsers.add_parser("analyze", help="分析规范化开奖数据")
    analyze_parser.add_argument("--in", dest="in_path", default="data/draws.csv", help="输入CSV路径")
    analyze_parser.add_argument("--report", default="out/report.md", help="输出Markdown报告路径")
    analyze_parser.add_argument("--json", dest="json_path", default="out/metrics.json", help="输出指标JSON路径")
    analyze_parser.set_defaults(handler=_handle_analyze)

    generate_parser = subparsers.add_parser("generate", help="根据历史数据生成推荐号码")
    generate_parser.add_argument("--in", dest="in_path", default="data/draws.csv", help="输入CSV路径")
    generate_parser.add_argument("--count", type=int, default=5, help="生成注数，默认5")
    generate_parser.add_argument(
        "--strategy", choices=("weighted", "uniform"), default="weighted", help="生成策略"
    )
    generate_parser.add_argument("--seed", type=int, default=None, help="随机种子，可复现结果")
    generate_parser.add_argument("--out", default="out/picks.txt", help="输出推荐号码文件")
    generate_parser.set_defaults(handler=_handle_generate)

    return parser


def _handle_fetch(args: argparse.Namespace) -> int:
    years = max(args.years, 1)
    LOGGER.info("开始抓取近 %s 年数据，来源：%s", years, args.source)

    draws = []
    if args.source == "official":
        try:
            draws = official.fetch_draws(years=years, sleep=args.sleep)
            LOGGER.info("官方来源抓取成功，共 %d 期", len(draws))
        except FetchError as exc:
            LOGGER.warning("官方抓取失败（%s），尝试回退至500.com", exc)
            draws = five_hundred.fetch_draws(years=years)
            LOGGER.info("500.com 抓取成功，共 %d 期", len(draws))
    else:
        draws = five_hundred.fetch_draws(years=years)
        LOGGER.info("500.com 抓取成功，共 %d 期", len(draws))

    frame = normalise_draws(draws)
    if frame.empty:
        raise FetchError("无法获取任何开奖数据")

    save_draws(frame, args.out)
    LOGGER.info("规范化数据已保存至 %s", args.out)
    return 0


def _handle_analyze(args: argparse.Namespace) -> int:
    frame = load_draws(args.in_path)
    metrics = compute_metrics(frame)
    report_text = render_report(metrics)
    save_report(report_text, args.report)
    save_metrics(metrics, args.json_path)
    LOGGER.info("分析完成，报告：%s，指标：%s", args.report, args.json_path)
    return 0


def _handle_generate(args: argparse.Namespace) -> int:
    picks = generate_from_file(args.in_path, count=args.count, strategy=args.strategy, seed=args.seed)
    save_picks(picks, args.out)
    for pick in picks:
        LOGGER.info("推荐：%s", pick.to_line())
    LOGGER.info("共生成 %d 注号码，已保存至 %s", len(picks), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
