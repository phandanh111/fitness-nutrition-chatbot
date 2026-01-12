"""Utility script to (re)build the exercise semantic index."""

import argparse
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.unified_rag import build_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or refresh RAG index for exercises.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Xóa collection cũ và build lại hoàn toàn.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.force:
        print("Rebuilding semantic indexes (force refresh)...")
        print("  → Building exercise index...")
        build_index("exercises", force_refresh=True)
    else:
        print("Updating semantic indexes (incremental)...")
        print("  → Updating exercise index...")
        build_index("exercises", force_refresh=False)
    print("Done.")


if __name__ == "__main__":
    main()


