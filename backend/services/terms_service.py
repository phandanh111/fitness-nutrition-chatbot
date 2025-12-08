"""Terms-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from rag.unified_rag import semantic_search
from services.llm_service import get_ai_response
from constants.rag_prompts import get_rag_system_prompt

MAX_CONTEXT_TERMS = int(os.getenv("TERMS_CONTEXT_LIMIT", "5"))


def build_context_from_terms(terms_results: List[Dict]) -> List[str]:
    """Xây dựng context từ danh sách terms search results."""
    contexts: List[str] = []
    for result in terms_results[:MAX_CONTEXT_TERMS]:
        document = result.get("document", "")
        if document:
            contexts.append(document)
    return contexts


def generate_answer_from_context(question: str, context_blocks: List[str], extra_guidance: Optional[str] = None) -> str:
    """Tạo câu trả lời từ context."""
    if not context_blocks:
        return "Xin lỗi, mình chưa tìm thấy thông tin về điều khoản điều kiện này trong dữ liệu hiện có."

    # Kết hợp context blocks thành một text liền mạch, không đánh số đoạn
    context_text = "\n\n".join(context_blocks)
    guidance_lines = [
        "QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong ngữ cảnh bên trên.",
        "TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về điều khoản, điều kiện, hoặc bất kỳ thông tin nào khác.",
        "Nếu ngữ cảnh không chứa thông tin về điều khoản được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy thông tin về điều khoản này' và KHÔNG được liệt kê các thông tin không có trong ngữ cảnh.",
        "TUYỆT ĐỐI KHÔNG được tự động gợi ý các điều khoản hoặc thông tin khác nếu câu hỏi không liên quan đến thông tin trong ngữ cảnh.",
        "- Trả lời một cách TỰ NHIÊN, như đang giải thích cho khách hàng, KHÔNG được trích dẫn nguyên văn hoặc đề cập đến 'đoạn', 'phần', 'mục' trong ngữ cảnh.",
        "- Tổng hợp thông tin từ ngữ cảnh và trình bày một cách mạch lạc, dễ hiểu, như một người tư vấn đang giải thích.",
        "- Giữ giọng điệu thân thiện, chuyên nghiệp, tự nhiên, dùng đại từ 'mình'/'bạn'.",
        "- Trả lời bằng tiếng Việt, câu văn mềm mại, ngắn gọn, tránh lặp lại.",
        "- KHÔNG được nói 'theo đoạn X', 'trong phần Y', hoặc bất kỳ tham chiếu nào đến cấu trúc của ngữ cảnh.",
    ]
    if extra_guidance:
        guidance_lines.append(f"- {extra_guidance}")

    prompt = (
        f"Ngữ cảnh về điều khoản điều kiện của The New Gym:\n\n{context_text}\n\n"
        f"Hướng dẫn:\n" + "\n".join(guidance_lines) + "\n\n"
        f"Câu hỏi của khách: {question}\n\n"
        f"LƯU Ý CUỐI CÙNG: Trả lời một cách TỰ NHIÊN như đang tư vấn trực tiếp cho khách hàng. "
        f"KHÔNG được trích dẫn nguyên văn, KHÔNG đề cập đến số đoạn, phần, mục. "
        f"Chỉ giải thích thông tin một cách mạch lạc và dễ hiểu dựa trên ngữ cảnh được cung cấp."
    )
    messages = [{"role": "user", "content": prompt}]
    return get_ai_response(messages, get_rag_system_prompt("terms"))


def is_terms_related_query(message: str) -> bool:
    """Phát hiện câu hỏi về điều khoản điều kiện bằng semantic search."""
    try:
        from utils.query_classifier import is_terms_query
        return is_terms_query(message)
    except Exception as e:
        print(f"[TermsService] Error in is_terms_related_query: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_terms_response(message: str) -> str:
    """Tạo câu trả lời cho câu hỏi về điều khoản điều kiện."""
    # Thử semantic search
    semantic_results: List[Dict] = []
    try:
        semantic_results = semantic_search("terms", message, top_k=MAX_CONTEXT_TERMS)
    except Exception as exc:
        print(f"[TermsService] semantic_search failed: {exc}")
        import traceback
        traceback.print_exc()

    # Chỉ sử dụng kết quả nếu score tốt (score < 0.85 nghĩa là tương đồng tốt)
    SEMANTIC_SCORE_THRESHOLD = 0.85
    if semantic_results:
        # Lọc các kết quả có score tốt (score < threshold)
        good_results = [
            item for item in semantic_results 
            if item.get("score") is not None and item.get("score") < SEMANTIC_SCORE_THRESHOLD
        ]
        
        if good_results:
            contexts = build_context_from_terms(good_results)
            return generate_answer_from_context(message, contexts)

    # Nếu không tìm thấy kết quả semantic search phù hợp (score quá cao = không tương đồng)
    # Trả về thông báo chung - không dùng keyword check, hoàn toàn dựa vào vector similarity
    return "Mình chưa tìm thấy thông tin về điều khoản điều kiện bạn đang hỏi. Bạn có thể mô tả cụ thể hơn về điều khoản bạn muốn tìm hiểu không?"

