"""Semantic search utilities for The New Gym clubs (embedding + vector DB)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding

from utils.clubs_client import clubs_client

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "rag"
CHROMA_DIR = DATA_DIR / "chroma"
HF_CACHE_DIR = DATA_DIR / "hf_cache"
META_PATH = DATA_DIR / "clubs_meta.json"
COLLECTION_NAME = "club_documents"

DEFAULT_EMBED_MODEL = os.getenv(
    "CLUB_EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
MAX_CLUBS_TO_EMBED = int(os.getenv("CLUB_EMBED_LIMIT", "2000"))

os.environ.setdefault("HF_HUB_ENABLE_HF_XET", "0")
os.environ.setdefault("HF_HUB_ENABLE_XET", "0")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR))

_chroma_client: chromadb.Client | None = None
_embedding_model = TextEmbedding(model_name=DEFAULT_EMBED_MODEL)


class FastEmbedFunction:
    def __call__(self, input: List[str]) -> List[List[float]]:
        return list(_embedding_model.embed(input))

    def name(self) -> str:
        return f"fastembed:{DEFAULT_EMBED_MODEL}"


def _ensure_data_dir() -> None:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_client() -> chromadb.Client:
    global _chroma_client
    if _chroma_client is None:
        _ensure_data_dir()
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_collection(reset: bool = False):
    client = _get_client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=FastEmbedFunction(),
    )


def _build_text_from_club(club: Dict) -> str:
    parts = [
        f"Tên: {club.get('nameVi') or club.get('nameEn') or ''}",
        f"Địa chỉ: {club.get('location') or club.get('address') or ''}",
    ]
    city = club.get("city", {}).get("cityName")
    district = club.get("district", {}).get("districtName")
    if district:
        parts.append(f"Quận/Huyện: {district}")
    if city:
        parts.append(f"Thành phố: {city}")
    if club.get("informationUrl"):
        parts.append(f"Link: {club['informationUrl']}")
    if club.get("description"):
        parts.append(f"Mô tả: {club['description']}")
    return "\n".join(filter(None, parts))


def build_club_index(force_refresh: bool = False) -> None:
    """Rebuild the club embedding index and persist metadata."""
    _ensure_data_dir()
    collection = _get_collection(reset=True if force_refresh else False)

    clubs = clubs_client.get_active_clubs(use_cache=not force_refresh)[:MAX_CLUBS_TO_EMBED]
    if not clubs:
        raise RuntimeError("Không có dữ liệu chi nhánh để xây dựng index.")

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict] = []
    metadata_dump: List[Dict] = []

    for idx, club in enumerate(clubs):
        doc_id = str(club.get("key") or club.get("id") or idx)
        ids.append(doc_id)
        documents.append(_build_text_from_club(club))
        metadatas.append(
            {
                "name": club.get("nameVi") or club.get("nameEn"),
                "city": club.get("city", {}).get("cityName"),
                "district": club.get("district", {}).get("districtName"),
                "link": club.get("informationUrl"),
                "raw": json.dumps(club, ensure_ascii=False),
            }
        )
        metadata_dump.append(
            {
                "id": doc_id,
                "name": club.get("nameVi") or club.get("nameEn"),
                "address": club.get("location") or club.get("address"),
                "city": club.get("city", {}).get("cityName"),
                "district": club.get("district", {}).get("districtName"),
                "link": club.get("informationUrl"),
                "raw": club,
            }
        )

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata_dump, f, ensure_ascii=False, indent=2)


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index."""
    if not query.strip():
        return []

    collection = _get_collection()
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
    except chromadb.errors.InvalidCollectionException:
        build_club_index(force_refresh=True)
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=top_k)

    if not results.get("ids"):
        return []

    docs: List[Dict] = []
    for idx, doc_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][idx] or {}
        raw_data = metadata.get("raw")
        raw_dict = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        docs.append(
            {
                "id": doc_id,
                "score": float(results.get("distances", [[0]])[0][idx]) if results.get("distances") else None,
                "document": results["documents"][0][idx],
                "raw": raw_dict,
            }
        )
    return docs


def refresh_club_index() -> None:
    build_club_index(force_refresh=True)
