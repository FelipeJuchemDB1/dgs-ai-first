"""Compatibility CLI for RAG POC.

This file is kept for backward compatibility and now delegates to the
separated scripts structure:
- scripts/ingest/ingest.py
- scripts/search/search.py
- scripts/prompt/prompt.py
"""

from __future__ import annotations

import argparse
import json
from scripts.common.rag_core import build_prompt, ingest_documents, print_rows, search_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG POC - NovaTech (compat mode)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingere documentos markdown no Chroma")
    p_ingest.add_argument("--docs-dir", default=".", help="Diretorio com documentos .md")
    p_ingest.add_argument("--max-tokens", type=int, default=500)
    p_ingest.add_argument("--overlap", type=float, default=0.1)

    p_search = sub.add_parser("search", help="Busca chunks similares")
    p_search.add_argument("--question", required=True)
    p_search.add_argument("--top-k", type=int, default=5)

    p_prompt = sub.add_parser("prompt", help="Monta prompt final para uso no LLM")
    p_prompt.add_argument("--question", required=True)
    p_prompt.add_argument("--top-k", type=int, default=5)

    args = parser.parse_args()

    if args.command == "ingest":
        summary = ingest_documents(args.docs_dir, max_tokens=args.max_tokens, overlap_ratio=args.overlap)
        print(json.dumps(summary, ensure_ascii=True))
        return

    if args.command == "search":
        rows = search_chunks(args.question, top_k=args.top_k)
        print_rows(rows)
        return

    if args.command == "prompt":
        rows = search_chunks(args.question, top_k=args.top_k)
        print(build_prompt(args.question, rows))
        return


if __name__ == "__main__":
    main()
