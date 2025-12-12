"""Unified RAG system với topic registry - cho phép đăng ký nhiều topics dễ dàng."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from rag.base_rag import BaseRAG, TopicParser, TopicTextBuilder, TopicMetadataBuilder

# Registry để lưu các RAG instances
_rag_registry: Dict[str, BaseRAG] = {}


def register_topic(
    topic_name: str,
    collection_name: str,
    parser: TopicParser,
    text_builder: TopicTextBuilder,
    metadata_builder: TopicMetadataBuilder,
    source_path: Optional[Path] = None,
    max_items: int = 1000,
) -> BaseRAG:
    """
    Đăng ký một topic mới vào RAG system.

    Args:
        topic_name: Tên topic (ví dụ: "clubs", "exercises")
        collection_name: Tên collection trong ChromaDB
        parser: Parser để parse dữ liệu
        text_builder: Builder để xây dựng text
        metadata_builder: Builder để xây dựng metadata
        source_path: Đường dẫn đến file source
        max_items: Số lượng items tối đa

    Returns:
        BaseRAG instance cho topic này
    """
    rag = BaseRAG(
        topic_name=topic_name,
        collection_name=collection_name,
        parser=parser,
        text_builder=text_builder,
        metadata_builder=metadata_builder,
        source_path=source_path,
        max_items=max_items,
    )
    _rag_registry[topic_name] = rag
    return rag


def get_rag(topic_name: str) -> Optional[BaseRAG]:
    """Lấy RAG instance cho một topic."""
    return _rag_registry.get(topic_name)


def semantic_search(topic_name: str, query: str, top_k: int = 5) -> list:
    """
    Semantic search cho một topic cụ thể.

    Args:
        topic_name: Tên topic (ví dụ: "clubs", "exercises")
        query: Query string
        top_k: Số lượng kết quả

    Returns:
        List of search results (empty list nếu có lỗi)
    """
    try:
        _ensure_topics_registered()
        rag = get_rag(topic_name)
        if rag is None:
            print(f"[UnifiedRAG] Warning: Topic '{topic_name}' chưa được đăng ký trong RAG system")
            return []
        return rag.semantic_search(query, top_k=top_k)
    except Exception as e:
        print(f"[UnifiedRAG] Error in semantic_search for topic '{topic_name}': {e}")
        import traceback
        traceback.print_exc()
        return []


def build_index(topic_name: str, force_refresh: bool = False, **kwargs) -> None:
    """
    Build index cho một topic.

    Args:
        topic_name: Tên topic
        force_refresh: Nếu True, xóa và build lại
        **kwargs: Additional kwargs cho parser
    """
    _ensure_topics_registered()
    rag = get_rag(topic_name)
    if rag is None:
        raise ValueError(f"Topic '{topic_name}' chưa được đăng ký trong RAG system")
    rag.build_index(force_refresh=force_refresh, **kwargs)


def refresh_index(topic_name: str) -> None:
    """Refresh index cho một topic."""
    _ensure_topics_registered()
    rag = get_rag(topic_name)
    if rag is None:
        raise ValueError(f"Topic '{topic_name}' chưa được đăng ký trong RAG system")
    rag.refresh_index()


def get_all_topics() -> list[str]:
    """Lấy danh sách tất cả topics đã đăng ký."""
    return list(_rag_registry.keys())


# Auto-register topics khi import (lazy để tránh circular import)
def _auto_register_topics():
    """Tự động đăng ký các topics khi module được import."""
    try:
        from rag.topics.clubs import register_clubs_topic
        from rag.topics.exercises import register_exercises_topic
        from rag.topics.terms import register_terms_topic
        from rag.topics.prices import register_prices_topic
        from rag.topics.inbody import register_inbody_topic

        register_clubs_topic()
        register_exercises_topic()
        register_terms_topic()
        register_prices_topic()
        register_inbody_topic()
    except ImportError as e:
        # Nếu chưa có topics, bỏ qua
        print(f"[UnifiedRAG] Warning: Could not import topics: {e}")
    except Exception as e:
        # Log lỗi nhưng không crash
        print(f"[UnifiedRAG] Error registering topics: {e}")
        import traceback
        traceback.print_exc()


# Lazy auto-register - chỉ register khi cần
def _ensure_topics_registered():
    """Đảm bảo topics đã được đăng ký."""
    if not _rag_registry:
        try:
            _auto_register_topics()
        except Exception as e:
            print(f"[UnifiedRAG] Error ensuring topics registered: {e}")
            import traceback
            traceback.print_exc()

