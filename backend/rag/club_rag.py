"""Semantic search utilities for The New Gym clubs (embedding + vector DB)."""

from __future__ import annotations

import json  # Chỉ dùng để serialize/deserialize raw data trong metadata
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding

try:
    from chromadb.errors import InvalidCollectionException as ChromaInvalidCollection
except Exception:  # pragma: no cover - fallback for version differences
    ChromaInvalidCollection = Exception

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "rag"
CLUBS_MD_PATH = BASE_DIR / "data" / "clubs.md"
CHROMA_DIR = DATA_DIR / "chroma"
HF_CACHE_DIR = DATA_DIR / "hf_cache"
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
    """Adapter để dùng FastEmbed với ChromaDB (tuân thủ API embed_documents/embed_query)."""

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return list(_embedding_model.embed(texts))

    def __call__(self, input: List[str]) -> List[List[float]]:  # legacy API
        return self._embed(input)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return self._embed(documents)

    def embed_query(self, query: str | List[str]) -> List[List[float]]:
        queries = [query] if isinstance(query, str) else query
        return self._embed(queries)

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
            client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=FastEmbedFunction(),
    )


def _parse_clubs_from_markdown(md_path: Path) -> List[Dict]:
    """Parse clubs từ file markdown."""
    if not md_path.exists():
        raise FileNotFoundError(f"File markdown không tồn tại: {md_path}")
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    clubs = []
    # Pattern để match mỗi CLB section: ## CLB X — Name (ID)
    pattern = r"## CLB (\d+) — (.+?) \(([A-Z0-9]+)\)\n(.*?)(?=\n## CLB|\Z)"
    
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        club_num = match.group(1)
        club_name = match.group(2).strip()
        club_id = match.group(3).strip()
        club_content = match.group(4).strip()
        
        # Parse các field từ content
        club_data = {
            "id": int(club_num),
            "key": club_id,
            "nameVi": "",
            "nameEn": "",
            "address": "",
            "location": "",
            "openDate": "",
            "isActive": 0,
            "informationUrl": "",
            "latitude": None,
            "longitude": None,
            "city": {},
            "district": {},
        }
        
        # Parse từng dòng
        for line in club_content.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Remove leading "- "
            if line.startswith("- "):
                line = line[2:].strip()
            
            # Parse các field
            if line.startswith("Tên tiếng Việt:"):
                club_data["nameVi"] = line.replace("Tên tiếng Việt:", "").strip()
            elif line.startswith("Tên tiếng Anh:"):
                club_data["nameEn"] = line.replace("Tên tiếng Anh:", "").strip()
            elif line.startswith("Địa chỉ:"):
                address = line.replace("Địa chỉ:", "").strip()
                club_data["address"] = address
                club_data["location"] = address
            elif line.startswith("Ngày mở:"):
                date_str = line.replace("Ngày mở:", "").strip()
                # Convert DD/MM/YYYY to ISO format
                if "/" in date_str:
                    parts = date_str.split("/")
                    if len(parts) == 3:
                        club_data["openDate"] = f"{parts[2]}-{parts[1]}-{parts[0]}T00:00:00.000Z"
            elif line.startswith("Hoạt động:"):
                is_active = line.replace("Hoạt động:", "").strip().lower()
                club_data["isActive"] = 1 if is_active == "có" else 0
            elif line.startswith("Website:"):
                club_data["informationUrl"] = line.replace("Website:", "").strip()
            elif line.startswith("Tọa độ:"):
                coords = line.replace("Tọa độ:", "").strip()
                if coords and coords != "Không có":
                    try:
                        lat, lon = map(float, coords.split(","))
                        club_data["latitude"] = lat
                        club_data["longitude"] = lon
                    except:
                        pass
        
        # Parse city và district từ địa chỉ
        if club_data["address"]:
            # Format: "địa chỉ, quận/huyện, thành phố, Việt Nam"
            parts = [p.strip() for p in club_data["address"].split(",")]
            if len(parts) >= 3:
                district_name = parts[-3] if len(parts) >= 3 else ""
                city_name = parts[-2] if len(parts) >= 2 else ""
                
                if district_name:
                    club_data["district"] = {"districtName": district_name}
                if city_name:
                    club_data["city"] = {"cityName": city_name}
        
        clubs.append(club_data)
    
    return clubs


def _build_text_from_club(club: Dict) -> str:
    """Xây dựng text chunk chi tiết từ club data."""
    # Lấy thông tin cơ bản
    name_vi = club.get("nameVi", "")
    name_en = club.get("nameEn", "")
    location = club.get("location", "") or club.get("address", "")
    
    # Thông tin địa lý
    city = ""
    district = ""
    if isinstance(club.get("city"), dict):
        city = club.get("city", {}).get("cityName", "")
    elif isinstance(club.get("city"), str):
        city = club.get("city", "")
    
    if isinstance(club.get("district"), dict):
        district = club.get("district", {}).get("districtName", "")
    elif isinstance(club.get("district"), str):
        district = club.get("district", "")
    
    # Thông tin khác
    info_url = club.get("informationUrl", "")
    
    # Xây dựng text chunk
    parts = []
    
    # Tên chi nhánh (ưu tiên tiếng Việt)
    if name_vi:
        parts.append(f"Chi nhánh: {name_vi}")
        if name_en and name_en != name_vi:
            parts.append(f"Tên tiếng Anh: {name_en}")
    elif name_en:
        parts.append(f"Chi nhánh: {name_en}")
    
    # Địa chỉ đầy đủ
    if location:
        parts.append(f"Địa chỉ: {location}")
    
    # Thông tin địa lý chi tiết
    location_parts = []
    if district:
        location_parts.append(district)
    if city:
        location_parts.append(city)
    
    if location_parts:
        parts.append(f"Khu vực: {', '.join(location_parts)}")
    
    # Link thông tin
    if info_url:
        parts.append(f"Trang web: {info_url}")
    
    # Thông tin bổ sung (tọa độ, ngày mở cửa)
    if club.get("latitude") and club.get("longitude"):
        parts.append(f"Tọa độ: {club.get('latitude')}, {club.get('longitude')}")
    
    if club.get("openDate"):
        parts.append(f"Ngày mở cửa: {club.get('openDate')}")
    
    # Trạng thái
    is_active = club.get("isActive", 0)
    status = "Đang hoạt động" if is_active == 1 else "Tạm đóng"
    parts.append(f"Trạng thái: {status}")
    
    return "\n".join(parts)


def build_club_index(force_refresh: bool = False, source: str = "markdown") -> None:
    """
    Rebuild the club embedding index from markdown file.
    
    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
        source: Nguồn dữ liệu ("markdown" hoặc "api"). Mặc định: "markdown"
    """
    _ensure_data_dir()
    collection = _get_collection(reset=True if force_refresh else False)

    # Lấy dữ liệu clubs từ markdown
    if source == "markdown":
        clubs = _parse_clubs_from_markdown(CLUBS_MD_PATH)
        # Lọc chỉ lấy clubs đang hoạt động
        clubs = [c for c in clubs if c.get("isActive") == 1][:MAX_CLUBS_TO_EMBED]
        source_name = "markdown"
    else:
        # Fallback về API nếu cần
        from utils.clubs_client import clubs_client
        clubs = clubs_client.get_active_clubs(use_cache=not force_refresh)[:MAX_CLUBS_TO_EMBED]
        source_name = "API"
    
    if not clubs:
        raise RuntimeError("Không có dữ liệu chi nhánh để xây dựng index.")

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict] = []

    for idx, club in enumerate(clubs):
        doc_id = str(club.get("key") or club.get("id") or idx)
        ids.append(doc_id)
        
        # Xây dựng text chunk từ club data
        text = _build_text_from_club(club)
        documents.append(text)
        
        # Xây dựng metadata
        city_name = ""
        district_name = ""
        if isinstance(club.get("city"), dict):
            city_name = club.get("city", {}).get("cityName", "")
        if isinstance(club.get("district"), dict):
            district_name = club.get("district", {}).get("districtName", "")
        
        metadatas.append(
            {
                "name": club.get("nameVi") or club.get("nameEn"),
                "city": city_name,
                "district": district_name,
                "link": club.get("informationUrl"),
                "raw": json.dumps(club, ensure_ascii=False),
            }
        )

    if not ids:
        raise RuntimeError("Không có clubs hợp lệ để xây dựng index.")

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"[RAG] Đã xây dựng index với {len(ids)} clubs từ {source_name}")


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index."""
    if not query.strip():
        return []

    collection = _get_collection()
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
    except ChromaInvalidCollection:
        build_club_index(force_refresh=True)
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=top_k)
    except Exception as exc:
        print(f"[RAG] Query failed: {exc}")
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


def refresh_club_index() -> None:
    build_club_index(force_refresh=True)
