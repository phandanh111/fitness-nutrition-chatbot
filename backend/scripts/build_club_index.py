"""Utility script to (re)build the club semantic index."""

import argparse
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.club_rag import build_club_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or refresh RAG index for clubs.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Xóa collection cũ và build lại hoàn toàn.",
    )
    parser.add_argument(
        "--source",
        choices=["markdown", "api"],
        default="markdown",
        help="Nguồn dữ liệu để build index (mặc định: markdown).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.force:
        print("Rebuilding club semantic index (force refresh)...")
        build_club_index(force_refresh=True, source=args.source)
    else:
        print("Updating club semantic index (incremental)...")
        build_club_index(force_refresh=False, source=args.source)
    print("Done.")


if __name__ == "__main__":
    main()


