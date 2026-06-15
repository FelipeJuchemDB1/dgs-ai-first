from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common.rag_core import build_prompt, search_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Monta prompt final para uso no LLM")
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    rows = search_chunks(args.question, top_k=args.top_k)
    prompt = build_prompt(args.question, rows)
    print(prompt)


if __name__ == "__main__":
    main()
