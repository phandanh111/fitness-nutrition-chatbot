"""Utility script to (re)build the club semantic index."""

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.club_rag import refresh_club_index  # noqa: E402


def main() -> None:
    print("Rebuilding club semantic index...")
    refresh_club_index()
    print("Done.")


if __name__ == "__main__":
    main()


