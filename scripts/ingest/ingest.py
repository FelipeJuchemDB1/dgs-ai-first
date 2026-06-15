from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common.rag_core import ingest_documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestao de documentos para RAG POC")
    parser.add_argument("--docs-dir", default=".", help="Diretorio com arquivos .md")
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--overlap", type=float, default=0.1)
    args = parser.parse_args()

    summary = ingest_documents(args.docs_dir, max_tokens=args.max_tokens, overlap_ratio=args.overlap)
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
