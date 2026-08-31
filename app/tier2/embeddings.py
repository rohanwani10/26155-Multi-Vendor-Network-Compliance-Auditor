"""Embedding-similarity lookup against previously human-resolved patterns.
Empty until Phase 4's Training UI starts writing to it - that's expected;
every line is a genuine cache miss (-> LLM) the first time it's ever seen."""

import os
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_data")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
SIMILARITY_THRESHOLD = float(os.environ.get("EMBEDDING_MATCH_THRESHOLD", "0.9"))

COLLECTION_NAME = "learned_patterns"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    # anonymized_telemetry=False: this tool's whole premise is on-prem /
    # air-gap-friendly handling of sensitive device configs (PRD G3), so
    # Chroma must never phone home, even anonymized usage stats.
    settings = chromadb.Settings(anonymized_telemetry=False)
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR, settings=settings)


def _collection():
    # Explicit cosine space so "similarity = 1 - distance" below is correct
    # regardless of Chroma's own default metric.
    return _client().get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def embed(text: str) -> list[float]:
    return _model().encode(text).tolist()


def find_learned_match(vendor: str, line: str) -> dict | None:
    """Closest previously human-resolved pattern for this line, if any is
    within the similarity threshold. None on a cache miss."""
    collection = _collection()
    if collection.count() == 0:
        return None

    result = collection.query(
        query_embeddings=[embed(line)],
        n_results=1,
        where={"vendor": vendor},
    )
    ids = result.get("ids", [[]])[0]
    if not ids:
        return None

    similarity = 1 - result["distances"][0][0]
    if similarity < SIMILARITY_THRESHOLD:
        return None

    metadata = result["metadatas"][0][0]
    return {
        "category": metadata["category"],
        "field": metadata["field"],
        "value": metadata["value"],
        "confidence": similarity,
    }


def learn_pattern(vendor: str, line: str, category: str, field: str, value: str) -> None:
    """Persist a human-resolved mapping so future identical/similar lines
    resolve via embedding match instead of hitting the LLM again."""
    _collection().upsert(
        ids=[f"{vendor}:{line}"],
        embeddings=[embed(line)],
        metadatas=[{"vendor": vendor, "category": category, "field": field, "value": value}],
        documents=[line],
    )
