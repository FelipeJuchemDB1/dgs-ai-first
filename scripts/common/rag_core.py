from __future__ import annotations

import glob
import os
import re
from typing import Any, Iterable

COLLECTION_NAME = "novatech_rag_poc"
CHROMA_DIR = ".chroma"


def extract_version(file_name: str) -> str:
    lower = file_name.lower()
    if "v2" in lower or "-v2" in lower:
        return "v2"
    if "proc-042" in lower:
        return "v1"
    return "na"


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return max(1, int(words / 0.75))


def split_by_headings(markdown_text: str) -> list[tuple[str, str]]:
    lines = markdown_text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = "sem_titulo"
    current_lines: list[str] = []

    heading_pattern = re.compile(r"^#{1,6}\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line)
        if match:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return [(title, "\n".join(content).strip()) for title, content in sections if "\n".join(content).strip()]


def chunk_text(section_text: str, max_tokens: int = 500, overlap_ratio: float = 0.1) -> list[str]:
    words = section_text.split()
    if not words:
        return []

    max_words = max(100, int(max_tokens * 0.75))
    overlap_words = int(max_words * overlap_ratio)

    if len(words) <= max_words:
        return [section_text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_words)
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = max(0, end - overlap_words)

    return chunks


def iter_document_paths(docs_dir: str) -> Iterable[str]:
    pattern = os.path.join(docs_dir, "*.md")
    for path in sorted(glob.glob(pattern)):
        base = os.path.basename(path).lower()
        if base.startswith("cenario-") or base.startswith("readme"):
            continue
        yield path


def load_dependencies() -> tuple[Any, Any, Any]:
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Dependencias ausentes. Instale com: pip install chromadb sentence-transformers"
        ) from exc

    return chromadb, Settings, SentenceTransformer


def get_collection(chroma_dir: str = CHROMA_DIR):
    chromadb, Settings, _ = load_dependencies()
    client = chromadb.PersistentClient(path=chroma_dir, settings=Settings(anonymized_telemetry=False))
    return client.get_or_create_collection(name=COLLECTION_NAME)


def ingest_documents(docs_dir: str, max_tokens: int = 500, overlap_ratio: float = 0.1) -> dict[str, int]:
    _, _, SentenceTransformer = load_dependencies()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    collection = get_collection()

    docs_count = 0
    chunks_count = 0

    for path in iter_document_paths(docs_dir):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        file_name = os.path.basename(path)
        version = extract_version(file_name)
        sections = split_by_headings(text)

        to_add_ids: list[str] = []
        to_add_docs: list[str] = []
        to_add_meta: list[dict[str, Any]] = []

        local_chunk_index = 0
        for section_title, section_text in sections:
            for piece in chunk_text(section_text, max_tokens=max_tokens, overlap_ratio=overlap_ratio):
                chunk_id = f"{file_name}:{local_chunk_index}"
                local_chunk_index += 1

                to_add_ids.append(chunk_id)
                to_add_docs.append(piece)
                to_add_meta.append(
                    {
                        "doc": file_name,
                        "section": section_title,
                        "version": version,
                        "tokens_est": estimate_tokens(piece),
                    }
                )

        if to_add_ids:
            embeddings = model.encode(to_add_docs, normalize_embeddings=True).tolist()
            collection.upsert(ids=to_add_ids, documents=to_add_docs, metadatas=to_add_meta, embeddings=embeddings)
            docs_count += 1
            chunks_count += len(to_add_ids)

    return {"documents": docs_count, "chunks": chunks_count}


def search_chunks(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    _, _, SentenceTransformer = load_dependencies()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    collection = get_collection()
    q_emb = model.encode([question], normalize_embeddings=True).tolist()

    result = collection.query(query_embeddings=q_emb, n_results=top_k)

    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    rows: list[dict[str, Any]] = []
    for cid, doc_text, meta, dist in zip(ids, docs, metas, dists):
        rows.append(
            {
                "chunk_id": cid,
                "doc": meta.get("doc", "na"),
                "section": meta.get("section", "na"),
                "version": meta.get("version", "na"),
                "distance": float(dist),
                "score": float(1.0 - dist),
                "text": doc_text,
            }
        )

    return rows


def build_prompt(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    system_prompt = (
        "Voce e assistente de atendimento da NovaTech. "
        "Use apenas o contexto recuperado. "
        "Sempre cite fonte. "
        "Nunca invente prazos ou valores. "
        "Se faltar informacao, diga explicitamente e sugira escalar para supervisor."
    )

    context_lines = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        context_lines.append(
            "\n".join(
                [
                    f"[Chunk {i}] id={chunk['chunk_id']}",
                    f"fonte={chunk['doc']} | secao={chunk['section']} | versao={chunk['version']} | score={chunk['score']:.4f}",
                    chunk["text"],
                ]
            )
        )

    context_block = "\n\n".join(context_lines)

    return (
        f"SYSTEM:\n{system_prompt}\n\n"
        f"CONTEXTO:\n{context_block}\n\n"
        f"PERGUNTA:\n{question}\n\n"
        "FORMATO DA RESPOSTA: resposta objetiva; Fonte(s); Dados faltantes (se houver)."
    )


def print_rows(rows: list[dict[str, Any]]) -> None:
    for i, row in enumerate(rows, start=1):
        print(
            f"{i}. {row['chunk_id']} | doc={row['doc']} | secao={row['section']} | versao={row['version']} | score={row['score']:.4f}"
        )
