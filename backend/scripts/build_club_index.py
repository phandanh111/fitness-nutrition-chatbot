"""Utility script to (re)build the club, exercise, terms, prices, and inbody semantic indexes."""

import argparse
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.unified_rag import build_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or refresh RAG indexes for clubs, exercises, terms, prices, and inbody.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Xóa collection cũ và build lại hoàn toàn.",
    )
    parser.add_argument(
        "--source",
        choices=["markdown", "api"],
        default="markdown",
        help="Nguồn dữ liệu để build club index (mặc định: markdown).",
    )
    parser.add_argument(
        "--skip-exercises",
        action="store_true",
        help="Bỏ qua việc build exercise index.",
    )
    parser.add_argument(
        "--skip-terms",
        action="store_true",
        help="Bỏ qua việc build terms index.",
    )
    parser.add_argument(
        "--skip-prices",
        action="store_true",
        help="Bỏ qua việc build prices index.",
    )
    parser.add_argument(
        "--skip-inbody",
        action="store_true",
        help="Bỏ qua việc build inbody index.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.force:
        print("Rebuilding semantic indexes (force refresh)...")
        print("  → Building club index...")
        build_index("clubs", force_refresh=True, source=args.source)
        if not args.skip_exercises:
            print("  → Building exercise index...")
            build_index("exercises", force_refresh=True)
        if not args.skip_terms:
            print("  → Building terms index...")
            build_index("terms", force_refresh=True)
        if not args.skip_prices:
            print("  → Building prices index...")
            build_index("prices", force_refresh=True)
        if not args.skip_inbody:
            print("  → Building inbody index...")
            build_index("inbody", force_refresh=True)
    else:
        print("Updating semantic indexes (incremental)...")
        print("  → Updating club index...")
        build_index("clubs", force_refresh=False, source=args.source)
        if not args.skip_exercises:
            print("  → Updating exercise index...")
            build_index("exercises", force_refresh=False)
        if not args.skip_terms:
            print("  → Updating terms index...")
            build_index("terms", force_refresh=False)
        if not args.skip_prices:
            print("  → Updating prices index...")
            build_index("prices", force_refresh=False)
        if not args.skip_inbody:
            print("  → Updating inbody index...")
            build_index("inbody", force_refresh=False)
    print("Done.")


if __name__ == "__main__":
    main()


