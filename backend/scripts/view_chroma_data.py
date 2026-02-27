"""
Script để xem dữ liệu trong ChromaDB một cách dễ đọc.
"""

import sqlite3
import json
import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "rag" / "chroma" / "chroma.sqlite3"

if not DB_PATH.exists():
    print(f"❌ Database không tồn tại: {DB_PATH}")
    print("💡 Hãy chạy: python backend/scripts/build_exercise_index.py để build index trước")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # Để truy cập theo tên cột
cursor = conn.cursor()

print("=" * 80)
print("CHROMADB DATA VIEWER")
print("=" * 80)
print()

# 1. Xem Collections
print("📋 COLLECTIONS:")
print("-" * 80)
cursor.execute("SELECT * FROM collections")
collections = cursor.fetchall()
for row in collections:
    print(f"  Name: {row['name']}")
    print(f"  ID: {row['id']}")
    print()
collection_id = collections[0]['id'] if collections else None

# 2. Xem Embeddings
print("📄 EMBEDDINGS (10 đầu tiên):")
print("-" * 80)
cursor.execute("SELECT * FROM embeddings LIMIT 10")
embeddings = cursor.fetchall()
for idx, row in enumerate(embeddings, 1):
    print(f"\n[{idx}] Embedding ID: {row['embedding_id']}")
    print(f"    Internal ID: {row['id']}")
    print(f"    Segment ID: {row['segment_id']}")
    print(f"    Seq ID: {row['seq_id']}")
    print(f"    Created At: {row['created_at']}")

# 3. Xem Metadata chi tiết cho từng embedding
print("\n" + "=" * 80)
print("📋 METADATA & DOCUMENTS:")
print("=" * 80)

# Lấy danh sách embeddings với internal ID
cursor.execute("SELECT id, embedding_id FROM embeddings LIMIT 10")
embeddings_map = {row[0]: row[1] for row in cursor.fetchall()}  # internal_id -> embedding_id

for idx, (internal_id, emb_id) in enumerate(embeddings_map.items(), 1):
    print(f"\n[Document {idx}] Embedding ID: {emb_id} (Internal ID: {internal_id})")
    print("-" * 80)
    
    # Lấy tất cả metadata cho embedding này (dùng internal_id)
    cursor.execute("""
        SELECT key, string_value, int_value, float_value, bool_value 
        FROM embedding_metadata 
        WHERE id = ?
        ORDER BY key
    """, (internal_id,))
    
    metadata_rows = cursor.fetchall()
    
    if not metadata_rows:
        print("  (Không có metadata)")
    else:
        for meta_row in metadata_rows:
            key = meta_row['key']
            # Lấy value từ bất kỳ cột nào có giá trị
            value = None
            if meta_row['string_value']:
                value = meta_row['string_value']
            elif meta_row['int_value'] is not None:
                value = meta_row['int_value']
            elif meta_row['float_value'] is not None:
                value = meta_row['float_value']
            elif meta_row['bool_value'] is not None:
                value = bool(meta_row['bool_value'])
            
            if value is None:
                continue
                
            if key == 'chroma:document':
                print(f"  📄 Document Text:")
                doc_lines = str(value).split('\n')
                for line in doc_lines[:10]:  # Hiển thị 10 dòng đầu
                    print(f"     {line}")
                if len(doc_lines) > 10:
                    print(f"     ... ({len(doc_lines) - 10} dòng nữa)")
            elif key == 'raw':
                try:
                    raw_data = json.loads(value)
                    print(f"  📦 Raw Data: <JSON, {len(str(raw_data))} chars>")
                    # Hiển thị một vài field quan trọng
                    if isinstance(raw_data, dict):
                        print(f"     - nameVi: {raw_data.get('nameVi', 'N/A')}")
                        print(f"     - location: {raw_data.get('location', 'N/A')}")
                        city_info = raw_data.get('city', {})
                        if isinstance(city_info, dict):
                            print(f"     - city: {city_info.get('cityName', 'N/A')}")
                        else:
                            print(f"     - city: N/A")
                except:
                    print(f"  📦 Raw Data: {str(value)[:100]}...")
            else:
                # Hiển thị value ngắn gọn
                str_val = str(value)
                if len(str_val) > 100:
                    print(f"  {key}: {str_val[:100]}...")
                else:
                    print(f"  {key}: {value}")

# 4. Thông tin về vectors
print("\n" + "=" * 80)
print("🔢 THÔNG TIN VECTORS:")
print("=" * 80)
print("💡 Vectors được lưu trong ChromaDB dưới dạng binary")
print("   - Kích thước mỗi vector: 384 dimensions")
print("   - Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("   - Format: float32 array (4 bytes per dimension)")
print("   - Tổng kích thước mỗi vector: ~1.5 KB (384 * 4 bytes)")

# 5. Thống kê
print("\n" + "=" * 80)
print("📊 THỐNG KÊ:")
print("-" * 80)
cursor.execute("SELECT COUNT(*) FROM embeddings")
total_embeddings = cursor.fetchone()[0]
print(f"Tổng số embeddings: {total_embeddings}")

cursor.execute("SELECT COUNT(DISTINCT id) FROM embedding_metadata WHERE key = 'chroma:document'")
total_documents = cursor.fetchone()[0]
print(f"Tổng số documents: {total_documents}")

# Tính kích thước vectors
estimated_vector_size = total_embeddings * 384 * 4  # 384 dims * 4 bytes
print(f"Kích thước vectors ước tính: {estimated_vector_size / 1024:.2f} KB")

db_size = DB_PATH.stat().st_size
print(f"Kích thước database: {db_size / 1024 / 1024:.2f} MB")

# 6. Xem chi tiết vectors
print("\n" + "=" * 80)
print("📈 CHI TIẾT VECTORS (3 đầu tiên):")
print("=" * 80)

cursor.execute("SELECT embedding_id FROM embeddings LIMIT 3")
embedding_ids = [row[0] for row in cursor.fetchall()]

for emb_id in embedding_ids:
    print(f"\n[Embedding ID: {emb_id}]")
    
    # Lấy internal ID
    cursor.execute("SELECT id FROM embeddings WHERE embedding_id = ? LIMIT 1", (emb_id,))
    internal_id_row = cursor.fetchone()
    if not internal_id_row:
        continue
    internal_id = internal_id_row[0]
    
    # Lấy metadata
    cursor.execute("""
        SELECT key, string_value 
        FROM embedding_metadata 
        WHERE id = ?
        AND key IN ('name', 'city', 'district')
    """, (internal_id,))
    
    metadata = cursor.fetchall()
    for row in metadata:
        print(f"  {row['key']}: {row['string_value']}")
    
    print(f"  Vector: <384 dimensions, binary data trong ChromaDB>")
    print(f"  💡 Để xem vector values, dùng ChromaDB Python client hoặc test_embeddings_simple.py")

print("\n" + "=" * 80)
print("💡 HƯỚNG DẪN:")
print("-" * 80)
print("Để xem tất cả documents, chạy:")
print("  python3 backend/scripts/view_chroma_data.py")
print()
print("Hoặc dùng SQLite với cú pháp đúng:")
print(f"  sqlite3 {DB_PATH}")
print()
print("Trong SQLite shell, nhớ thêm dấu ';' ở cuối mỗi câu lệnh:")
print("  SELECT * FROM embeddings LIMIT 10;")
print("  SELECT * FROM collections;")
print("  .mode column")
print("  .headers on")
print("  SELECT * FROM embedding_metadata WHERE id = 'HVT';")

conn.close()

