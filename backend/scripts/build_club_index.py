"""Utility script to (re)build the club and exercise semantic indexes."""

import argparse
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.club_rag import build_club_index  # noqa: E402
from rag.exercise_rag import build_exercise_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or refresh RAG indexes for clubs and exercises.")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.force:
        print("Rebuilding semantic indexes (force refresh)...")
        print("  → Building club index...")
        build_club_index(force_refresh=True, source=args.source)
        if not args.skip_exercises:
            print("  → Building exercise index...")
            build_exercise_index(force_refresh=True)
    else:
        print("Updating semantic indexes (incremental)...")
        print("  → Updating club index...")
        build_club_index(force_refresh=False, source=args.source)
        if not args.skip_exercises:
            print("  → Updating exercise index...")
            build_exercise_index(force_refresh=False)
    print("Done.")


if __name__ == "__main__":
    main()


