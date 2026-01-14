"""Base RAG class chung cho tất cả các topics."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
CHROMA_DIR = DATA_DIR / "chroma"
HF_CACHE_DIR = DATA_DIR / "hf_cache"

DEFAULT_EMBED_MODEL = os.getenv(
    "EMBED_MODEL",
    "dangvantuan/vietnamese-embedding",
)

os.environ.setdefault("HF_HUB_ENABLE_HF_XET", "0")
os.environ.setdefault("HF_HUB_ENABLE_XET", "0")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR))

_global_chroma_client: chromadb.Client | None = None
_global_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    """Lazy load embedding model (shared across all topics)."""
    global _global_embedding_model
    if _global_embedding_model is None:
        _global_embedding_model = SentenceTransformer(DEFAULT_EMBED_MODEL)
    return _global_embedding_model


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
        queries = input if input is not None else query
        if queries is None:
            raise ValueError("Either 'query' or 'input' must be provided")
        queries = [queries] if isinstance(queries, str) else queries
        return self._embed(queries)

    def name(self) -> str:
        return f"sentence-transformers:{DEFAULT_EMBED_MODEL}"


def _get_global_client() -> chromadb.Client:
    """Get shared ChromaDB client."""
    global _global_chroma_client
    if _global_chroma_client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _global_chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _global_chroma_client


class TopicParser(ABC):
    """Abstract base class cho topic parser."""

    @abstractmethod
    def parse(self, source_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """Parse dữ liệu từ source và trả về list of dicts."""
        pass


class TopicTextBuilder(ABC):
    """Abstract base class cho text builder."""

    @abstractmethod
    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk từ item data."""
        pass


class TopicMetadataBuilder(ABC):
    """Abstract base class cho metadata builder."""

    @abstractmethod
    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ item data."""
        pass


class BaseRAG:
    """Base RAG class chung cho tất cả topics."""

    def __init__(
        self,
        topic_name: str,
        collection_name: str,
        parser: TopicParser,
        text_builder: TopicTextBuilder,
        metadata_builder: TopicMetadataBuilder,
        source_path: Optional[Path] = None,
        max_items: int = 1000,
    ):
        """
        Initialize RAG cho một topic.

        Args:
            topic_name: Tên topic (ví dụ: "exercises")
            collection_name: Tên collection trong ChromaDB
            parser: Parser để parse dữ liệu từ source
            text_builder: Builder để xây dựng text từ item
            metadata_builder: Builder để xây dựng metadata từ item
            source_path: Đường dẫn đến file source (markdown, etc.)
            max_items: Số lượng items tối đa để embed
        """
        self.topic_name = topic_name
        self.collection_name = collection_name
        self.parser = parser
        self.text_builder = text_builder
        self.metadata_builder = metadata_builder
        self.source_path = source_path
        self.max_items = max_items
        self._client = None
        self._collection = None

    def _get_client(self) -> chromadb.Client:
        """Get ChromaDB client."""
        if self._client is None:
            self._client = _get_global_client()
        return self._client

    def _get_collection(self, reset: bool = False):
        """Get or create collection."""
        client = self._get_client()
        if reset:
            try:
                client.delete_collection(name=self.collection_name)
            except Exception:
                pass

        if self._collection is None or reset:
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=VietnameseEmbeddingFunction(),
            )
        return self._collection

    def build_index(self, force_refresh: bool = False, **parser_kwargs) -> None:
        """
        Build embedding index từ source data.

        Args:
            force_refresh: Nếu True, xóa collection cũ và tạo mới
            **parser_kwargs: Additional kwargs cho parser
        """
        if self.source_path is None:
            raise ValueError(f"source_path is required for topic '{self.topic_name}'")

        collection = self._get_collection(reset=force_refresh)

        # Parse dữ liệu từ source
        items = self.parser.parse(self.source_path, **parser_kwargs)
        items = items[:self.max_items]

        if not items:
            raise RuntimeError(f"Không có dữ liệu để xây dựng index cho topic '{self.topic_name}'.")

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict] = []

        for idx, item in enumerate(items):
            # Generate doc ID
            doc_id = str(item.get("id") or item.get("key") or idx)
            ids.append(doc_id)

            # Build text chunk
            text = self.text_builder.build_text(item)
            documents.append(text)

            # Build metadata (include raw data)
            metadata = self.metadata_builder.build_metadata(item)
            metadata["raw"] = json.dumps(item, ensure_ascii=False)
            metadatas.append(metadata)

        if not ids:
            raise RuntimeError(f"Không có items hợp lệ để xây dựng index cho topic '{self.topic_name}'.")

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[RAG] Đã xây dựng index cho topic '{self.topic_name}' với {len(ids)} items")

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Run semantic search using the embedding index.

        Args:
            query: Query string
            top_k: Số lượng kết quả trả về

        Returns:
            List of dicts với keys: id, score, document, raw (empty list nếu có lỗi)
        """
        if not query.strip():
            return []

        try:
            collection = self._get_collection()
        except Exception as exc:
            print(f"[BaseRAG] Error getting collection for topic '{self.topic_name}': {exc}")
            return []

        try:
            results = collection.query(query_texts=[query], n_results=top_k)
        except ChromaInvalidCollection:
            # Auto-rebuild nếu collection không tồn tại
            try:
                print(f"[BaseRAG] Collection not found for topic '{self.topic_name}', attempting to rebuild...")
                self.build_index(force_refresh=True)
                collection = self._get_collection()
                results = collection.query(query_texts=[query], n_results=top_k)
            except Exception as rebuild_exc:
                print(f"[BaseRAG] Error rebuilding index for topic '{self.topic_name}': {rebuild_exc}")
                import traceback
                traceback.print_exc()
                return []
        except Exception as exc:
            print(f"[BaseRAG] Query failed for topic '{self.topic_name}': {exc}")
            import traceback
            traceback.print_exc()
            return []

        if not results.get("ids") or not results["ids"][0]:
            return []

        docs: List[Dict] = []
        try:
            for idx, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][idx] if results.get("metadatas") and results["metadatas"][0] else {}
                raw_data = metadata.get("raw")
                raw_dict = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                docs.append(
                    {
                        "id": doc_id,
                        "score": float(results.get("distances", [[0]])[0][idx]) if results.get("distances") and results["distances"][0] else None,
                        "document": results["documents"][0][idx] if results.get("documents") and results["documents"][0] else "",
                        "raw": raw_dict,
                    }
                )
        except Exception as exc:
            print(f"[BaseRAG] Error processing search results for topic '{self.topic_name}': {exc}")
            import traceback
            traceback.print_exc()
            return []
        
        return docs

    def refresh_index(self) -> None:
        """Refresh index (force rebuild)."""
        self.build_index(force_refresh=True)

