"""
rag_engine.py — RAG memory engine for CTS Intelligence.

Three corpora:
  corpus_a: Methodology Bible — static, populated once
            Sources: docs/METHODOLOGY.md, pine_scripts/, trading_rules.py
  corpus_b: Market Memory — rolling 90 days, updated nightly
            Sources: Nifty 200 OHLCV summaries, VIX, sector leaders
  corpus_c: Trade Memory — perpetual, never deleted
            Sources: every trade taken with full context + post-mortem

Public interface:
  rag_query(question: str, corpus: str, top_k: int = 5) -> list[str]
  ingest_document(text: str, metadata: dict, corpus: str) -> None
  delete_old_documents(corpus: str, days: int) -> int
"""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded globals to avoid import-time heavy loads
_client = None
_embedding_fn = None
_collections = {}


def _get_client():
    """Lazy-init ChromaDB persistent client."""
    global _client
    if _client is None:
        import chromadb
        persist_dir = Path(settings.rag_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(persist_dir))
        logger.info(f"ChromaDB initialized at {persist_dir}")
    return _client


def _get_embedding_fn():
    """Lazy-init sentence-transformers embedding function."""
    global _embedding_fn
    if _embedding_fn is None:
        from chromadb.utils import embedding_functions
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        logger.info("Embedding model loaded: all-MiniLM-L6-v2")
    return _embedding_fn


def _get_collection(corpus: str):
    """Get or create a ChromaDB collection for the given corpus."""
    if corpus not in _collections:
        client = _get_client()
        ef = _get_embedding_fn()
        _collections[corpus] = client.get_or_create_collection(
            name=corpus,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )
    return _collections[corpus]


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into chunks by approximate token count (4 chars per token)."""
    char_chunk = chunk_size * 4
    char_overlap = overlap * 4

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_chunk
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(". ")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)
            if break_point > char_chunk // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - char_overlap

    return [c for c in chunks if len(c) > 20]


def _generate_id(text: str, metadata: dict) -> str:
    """Generate deterministic ID from content + metadata."""
    key = f"{text[:200]}:{metadata.get('source', '')}:{metadata.get('date', '')}"
    return hashlib.md5(key.encode()).hexdigest()


def ingest_document(text: str, metadata: dict, corpus: str) -> int:
    """
    Ingest a document into a corpus. Chunks text and embeds.
    Returns number of chunks ingested.
    """
    collection = _get_collection(corpus)
    chunks = _chunk_text(text)

    if not chunks:
        logger.warning(f"No chunks generated for document in {corpus}")
        return 0

    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_meta = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
        chunk_id = _generate_id(chunk, chunk_meta)
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({k: str(v) for k, v in chunk_meta.items()})

    # Upsert to handle re-ingestion gracefully
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info(f"Ingested {len(chunks)} chunks into {corpus}")
    return len(chunks)


def rag_query(question: str, corpus: str, top_k: int = 5) -> list[str]:
    """
    Query a corpus with a natural language question.
    Returns list of relevant text chunks.
    """
    collection = _get_collection(corpus)

    try:
        results = collection.query(query_texts=[question], n_results=top_k)
        documents = results.get("documents", [[]])[0]
        return documents
    except Exception as e:
        logger.error(f"RAG query failed on {corpus}: {e}")
        return []


def delete_old_documents(corpus: str, days: int) -> int:
    """
    Delete documents older than N days from a corpus.
    Uses the 'date' field in metadata.
    Returns count of deleted documents.
    """
    collection = _get_collection(corpus)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        # Get all documents with dates
        all_docs = collection.get(include=["metadatas"])

        ids_to_delete = []
        for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
            doc_date = meta.get("date", "")
            if doc_date and doc_date < cutoff:
                ids_to_delete.append(doc_id)

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} old documents from {corpus}")

        return len(ids_to_delete)
    except Exception as e:
        logger.error(f"Failed to delete old documents from {corpus}: {e}")
        return 0


def get_corpus_stats() -> dict:
    """Get document counts for all corpora."""
    stats = {}
    for corpus_name in ["corpus_a", "corpus_b", "corpus_c"]:
        try:
            collection = _get_collection(corpus_name)
            stats[corpus_name] = collection.count()
        except Exception:
            stats[corpus_name] = 0
    return stats
