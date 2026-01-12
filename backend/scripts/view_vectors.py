"""
Script để xem vectors đã lưu trong ChromaDB bằng ChromaDB client.
    
Mặc định hiển thị collection `exercises`.
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
except ImportError:
    print("❌ ChromaDB chưa được cài đặt.")
    print("💡 Hãy chạy: pip install chromadb")
    sys.exit(1)

from rag.base_rag import CHROMA_DIR, VietnameseEmbeddingFunction, _get_global_client

# Map topic -> collection name
TOPIC_CONFIG = {
    "exercises": "exercise_documents",
}


def _get_collection(topic: str, reset: bool = False):
    """Lấy collection theo topic (compat cho scripts cũ)."""
    if topic not in TOPIC_CONFIG:
        raise ValueError(f"Topic không hỗ trợ: {topic}. Chọn một trong {list(TOPIC_CONFIG)}")

    client = _get_global_client()
    if reset:
        try:
            client.delete_collection(name=TOPIC_CONFIG[topic])
        except Exception:
            pass
    return client.get_or_create_collection(
        name=TOPIC_CONFIG[topic],
        metadata={"hnsw:space": "cosine"},
        embedding_function=VietnameseEmbeddingFunction(),
    )


def view_vectors(topic: str):
    """Xem vectors trong ChromaDB."""
    print("=" * 80)
    print(f"CHROMADB VECTORS VIEWER — {topic}")
    print("=" * 80)
    print()
    
    if not CHROMA_DIR.exists():
        print(f"❌ ChromaDB directory không tồn tại: {CHROMA_DIR}")
        print("💡 Hãy chạy script build index tương ứng trước")
        return
    
    try:
        collection = _get_collection(topic)
    except Exception as e:
        print(f"❌ Không thể kết nối ChromaDB: {e}")
        print("💡 Hãy chạy script build index tương ứng trước")
        return
    
    # Lấy tất cả documents
    print("📦 Đang lấy dữ liệu từ ChromaDB...")
    results = collection.get()
    
    if not results.get("ids"):
        print("❌ Không có dữ liệu trong ChromaDB")
        print("💡 Hãy chạy script build index tương ứng")
        return
    
    ids = results["ids"]
    documents = results["documents"]
    metadatas = results["metadatas"]
    
    print(f"✅ Tìm thấy {len(ids)} vectors\n")
    
    # Thông tin về vectors
    print("=" * 80)
    print("🔢 THÔNG TIN VECTORS:")
    print("=" * 80)
    
    # Lấy một vector để xem kích thước
    try:
        sample_embedding = collection.get(ids=[ids[0]], include=["embeddings"])
        embeddings_list = sample_embedding.get("embeddings")
        if embeddings_list is not None:
            try:
                # Kiểm tra nếu là numpy array hoặc list
                if hasattr(embeddings_list, '__len__'):
                    if len(embeddings_list) > 0:
                        vector_dim = len(embeddings_list[0])
                        print(f"Kích thước mỗi vector: {vector_dim} dimensions")
                        print(f"Format: float32 array")
                        print(f"Kích thước ước tính: ~{vector_dim * 4 / 1024:.2f} KB per vector")
                    else:
                        print("⚠️  Không thể lấy vector dimensions (embeddings list rỗng)")
                else:
                    print("⚠️  Không thể lấy vector dimensions (embeddings không phải list/array)")
            except Exception as e:
                print(f"⚠️  Không thể lấy vector dimensions: {e}")
        else:
            print("⚠️  Không thể lấy vector dimensions (embeddings không có trong response)")
    except Exception as e:
        print(f"⚠️  Lỗi khi lấy vector dimensions: {e}")
    
    print()
    
    # Hiển thị chi tiết 5 vectors đầu tiên
    print("=" * 80)
    print("📈 CHI TIẾT VECTORS (5 đầu tiên):")
    print("=" * 80)
    
    for idx in range(min(5, len(ids))):
        print(f"\n[{idx + 1}] ID: {ids[idx]}")
        print("-" * 80)
        
        # Metadata
        if metadatas and metadatas[idx]:
            metadata = metadatas[idx]
            print("📋 Metadata:")
            for key, value in metadata.items():
                if key != "raw":  # Bỏ qua raw vì quá dài
                    print(f"   {key}: {value}")
        
        # Document text
        if documents and documents[idx]:
            doc = documents[idx]
            print(f"\n📄 Document Text ({len(doc)} ký tự):")
            doc_lines = doc.split('\n')
            for line in doc_lines[:8]:  # Hiển thị 8 dòng đầu
                print(f"   {line}")
            if len(doc_lines) > 8:
                print(f"   ... ({len(doc_lines) - 8} dòng nữa)")
        
        # Vector values (10 giá trị đầu tiên)
        try:
            vector_data = collection.get(ids=[ids[idx]], include=["embeddings"])
            embeddings_list = vector_data.get("embeddings")
            if embeddings_list is not None:
                try:
                    if hasattr(embeddings_list, '__len__') and len(embeddings_list) > 0:
                        vector = embeddings_list[0]
                        # Convert numpy array to list nếu cần
                        if hasattr(vector, 'tolist'):
                            vector = vector.tolist()
                        print(f"\n🔢 Vector ({len(vector)} dimensions):")
                        print(f"   First 10 values: {[f'{v:.6f}' for v in vector[:10]]}")
                        print(f"   Min: {min(vector):.6f}")
                        print(f"   Max: {max(vector):.6f}")
                        print(f"   Mean: {sum(vector)/len(vector):.6f}")
                    else:
                        print(f"\n⚠️  Không thể lấy vector values (embeddings list rỗng)")
                except Exception as e:
                    print(f"\n⚠️  Không thể lấy vector values: {e}")
            else:
                print(f"\n⚠️  Không thể lấy vector values (embeddings không có trong response)")
        except Exception as e:
            print(f"\n⚠️  Không thể lấy vector values: {e}")
    
    # Thống kê
    print("\n" + "=" * 80)
    print("📊 THỐNG KÊ:")
    print("=" * 80)
    print(f"Tổng số vectors: {len(ids)}")
    
    # Đếm theo city (hữu ích cho clubs, giữ lại cho compat)
    if metadatas:
        cities = {}
        for meta in metadatas:
            if meta and meta.get("city"):
                city = meta["city"]
                cities[city] = cities.get(city, 0) + 1
        
        if cities:
            print(f"\n📍 Phân bố theo thành phố:")
            for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True):
                print(f"   {city}: {count} clubs")
    
    print("\n" + "=" * 80)
    print("💡 HƯỚNG DẪN:")
    print("-" * 80)
    print("Để xem tất cả vectors, chạy:")
    print("  python backend/scripts/view_vectors.py --topic exercises")
    print()
    print("Để test query vectors, chạy:")
    print("  python backend/scripts/test_embeddings_simple.py")
    print()
    print("Để xem raw database, chạy:")
    print("  python backend/scripts/view_chroma_data.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View ChromaDB vectors by topic")
    parser.add_argument(
        "--topic",
        choices=list(TOPIC_CONFIG.keys()),
        default="exercises",
        help="Topic muốn xem. Mặc định: exercises",
    )
    args = parser.parse_args()
    view_vectors(topic=args.topic)

