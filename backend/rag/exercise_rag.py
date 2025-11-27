"""Semantic search utilities for The New Gym exercises (embedding + vector DB)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pyvi.ViTokenizer import tokenize

try:
    from chromadb.errors import InvalidCollectionException as ChromaInvalidCollection
except Exception:
    ChromaInvalidCollection = Exception

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "rag"
EXERCISE_MD_PATH = BASE_DIR / "data" / "exercise.md"
CHROMA_DIR = DATA_DIR / "chroma"
HF_CACHE_DIR = DATA_DIR / "hf_cache"
COLLECTION_NAME = "exercise_documents"

DEFAULT_EMBED_MODEL = os.getenv(
    "CLUB_EMBED_MODEL",
    "dangvantuan/vietnamese-embedding",
)
MAX_EXERCISES_TO_EMBED = int(os.getenv("EXERCISE_EMBED_LIMIT", "500"))

os.environ.setdefault("HF_HUB_ENABLE_HF_XET", "0")
os.environ.setdefault("HF_HUB_ENABLE_XET", "0")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR))

_chroma_client: chromadb.Client | None = None
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    """Lazy load embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(DEFAULT_EMBED_MODEL)
    return _embedding_model


class VietnameseEmbeddingFunction:
    """Adapter để dùng SentenceTransformer với Vietnamese tokenization cho ChromaDB."""

    def _tokenize_texts(self, texts: List[str]) -> List[str]:
        """Tokenize Vietnamese texts."""
        return [tokenize(text) for text in texts]

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Embed texts với Vietnamese tokenization."""
        model = _get_embedding_model()
        tokenized_texts = self._tokenize_texts(texts)
        embeddings = model.encode(tokenized_texts, convert_to_numpy=True)
        return embeddings.tolist()

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self._embed(input)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return self._embed(documents)

    def embed_query(self, query: str | List[str] = None, input: str | List[str] = None) -> List[List[float]]:
        # ChromaDB có thể gọi với keyword argument 'input' hoặc positional 'query'
        queries = input if input is not None else query
        if queries is None:
            raise ValueError("Either 'query' or 'input' must be provided")
        queries = [queries] if isinstance(queries, str) else queries
        return self._embed(queries)

    def name(self) -> str:
        return f"sentence-transformers:{DEFAULT_EMBED_MODEL}"


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
            client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=VietnameseEmbeddingFunction(),
    )


def parse_exercises_from_markdown(md_path: Path = None) -> List[Dict]:
    """
    Parse exercises từ file markdown (public function).
    
    Args:
        md_path: Đường dẫn đến file markdown. Nếu None, dùng EXERCISE_MD_PATH mặc định.
    
    Returns:
        List[Dict]: Danh sách exercises
    """
    if md_path is None:
        md_path = EXERCISE_MD_PATH
    return _parse_exercises_from_markdown(md_path)


def _parse_exercises_from_markdown(md_path: Path) -> List[Dict]:
    """Parse exercises từ file markdown."""
    if not md_path.exists():
        raise FileNotFoundError(f"File markdown không tồn tại: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    exercises = []
    # Pattern để match mỗi Bài Tập section: ## Bài Tập X — Name
    pattern = r"## Bài Tập (\d+) — (.+?)\n(.*?)(?=\n## Bài Tập|\Z)"

    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        exercise_num = match.group(1)
        exercise_name = match.group(2).strip()
        exercise_content = match.group(3).strip()

        # Parse các field từ content
        exercise_data = {
            "id": int(exercise_num),
            "name": exercise_name,
            "nameVi": "",
            "nameEn": "",
            "muscleGroup": "",
            "difficulty": "",
            "calories": "",
        }

        # Parse từng dòng
        for line in exercise_content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Remove leading "- "
            if line.startswith("- "):
                line = line[2:].strip()

            # Parse các field
            if line.startswith("Nhóm cơ:"):
                exercise_data["muscleGroup"] = line.replace("Nhóm cơ:", "").strip()
            elif line.startswith("Tên tiếng Việt:"):
                exercise_data["nameVi"] = line.replace("Tên tiếng Việt:", "").strip()
            elif line.startswith("Tên tiếng Anh:"):
                exercise_data["nameEn"] = line.replace("Tên tiếng Anh:", "").strip()
            elif line.startswith("Độ khó:"):
                exercise_data["difficulty"] = line.replace("Độ khó:", "").strip()
            elif line.startswith("Kcal tiêu thụ:"):
                exercise_data["calories"] = line.replace("Kcal tiêu thụ:", "").strip()
               
        exercises.append(exercise_data)

    return exercises


def _build_text_from_exercise(exercise: Dict) -> str:
    """Xây dựng text chunk chi tiết từ exercise data."""
    parts = []

    # Tên bài tập (ưu tiên tiếng Việt)
    name_vi = exercise.get("nameVi", "")
    name_en = exercise.get("nameEn", "")
    if name_vi:
        parts.append(f"Bài tập: {name_vi}")
        if name_en and name_en != name_vi:
            parts.append(f"Tên tiếng Anh: {name_en}")
    elif name_en:
        parts.append(f"Bài tập: {name_en}")
    elif exercise.get("name"):
        parts.append(f"Bài tập: {exercise.get('name')}")

    # Nhóm cơ
    muscle_group = exercise.get("muscleGroup", "")
    if muscle_group:
        parts.append(f"Nhóm cơ: {muscle_group}")

    # Độ khó (quan trọng cho việc tìm kiếm bài tập cho người mới)
    difficulty = exercise.get("difficulty", "")
    if difficulty:
        parts.append(f"Độ khó: {difficulty}")

    # Kcal tiêu thụ
    calories = exercise.get("calories", "")
    if calories:
        parts.append(f"Kcal tiêu thụ: {calories}")

    

    return "\n".join(parts)


def build_exercise_index(force_refresh: bool = False) -> None:
    """
    Rebuild the exercise embedding index from markdown file.

    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
    """
    _ensure_data_dir()
    collection = _get_collection(reset=True if force_refresh else False)

    # Lấy dữ liệu exercises từ markdown
    exercises = parse_exercises_from_markdown()
    exercises = exercises[:MAX_EXERCISES_TO_EMBED]

    if not exercises:
        raise RuntimeError("Không có dữ liệu bài tập để xây dựng index.")

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict] = []

    for idx, exercise in enumerate(exercises):
        doc_id = str(exercise.get("id") or idx)
        ids.append(doc_id)

        # Xây dựng text chunk từ exercise data
        text = _build_text_from_exercise(exercise)
        documents.append(text)

        # Xây dựng metadata
        metadatas.append(
            {
                "name": exercise.get("nameVi") or exercise.get("nameEn") or exercise.get("name"),
                "nameVi": exercise.get("nameVi", ""),
                "nameEn": exercise.get("nameEn", ""),
                "muscleGroup": exercise.get("muscleGroup", ""),
                "difficulty": exercise.get("difficulty", ""),
                "calories": exercise.get("calories", ""),
                "equipment": exercise.get("equipment", ""),
                "raw": json.dumps(exercise, ensure_ascii=False),
            }
        )

    if not ids:
        raise RuntimeError("Không có exercises hợp lệ để xây dựng index.")

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"[RAG] Đã xây dựng exercise index với {len(ids)} bài tập")


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index."""
    if not query.strip():
        return []

    collection = _get_collection()
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
    except ChromaInvalidCollection:
        build_exercise_index(force_refresh=True)
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=top_k)
    except Exception as exc:
        print(f"[RAG] Exercise query failed: {exc}")
        return []

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


def refresh_exercise_index() -> None:
    build_exercise_index(force_refresh=True)

