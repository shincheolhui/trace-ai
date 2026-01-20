# app/integrations/parsers/text_parser.py
"""텍스트 파일 파싱 (TXT, MD)"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def parse_text_file(file_path: Path) -> str:
    """텍스트 파일에서 내용 추출
    
    Args:
        file_path: 파일 경로
        
    Returns:
        추출된 텍스트
    """
    encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
    
    for encoding in encodings:
        try:
            content = file_path.read_text(encoding=encoding)
            logger.debug(f"[text_parser] Parsed {file_path.name} with {encoding}")
            return content
        except UnicodeDecodeError:
            continue
    
    # 모든 인코딩 실패 시 바이너리로 읽어서 최대한 복구
    logger.warning(f"[text_parser] Fallback to binary read for {file_path.name}")
    return file_path.read_bytes().decode("utf-8", errors="replace")


def parse_text_bytes(content: bytes, filename: str = "unknown") -> str:
    """바이트 데이터에서 텍스트 추출
    
    Args:
        content: 파일 바이트 내용
        filename: 파일명 (로깅용)
        
    Returns:
        추출된 텍스트
    """
    encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
    
    for encoding in encodings:
        try:
            text = content.decode(encoding)
            logger.debug(f"[text_parser] Parsed {filename} with {encoding}")
            return text
        except UnicodeDecodeError:
            continue
    
    logger.warning(f"[text_parser] Fallback decode for {filename}")
    return content.decode("utf-8", errors="replace")


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """텍스트를 청크로 분할
    
    Args:
        text: 분할할 텍스트
        chunk_size: 청크 크기 (문자 수)
        overlap: 오버랩 크기
        
    Returns:
        청크 리스트
    """
    settings = get_settings()
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    
    if not text or not text.strip():
        return []
    
    # 문단 기준으로 먼저 분리
    paragraphs = text.split("\n\n")
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 현재 청크 + 문단이 chunk_size 이하면 합침
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            # 현재 청크 저장
            if current_chunk:
                chunks.append(current_chunk)
            
            # 문단 자체가 chunk_size보다 크면 강제 분할
            if len(para) > chunk_size:
                words = para.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= chunk_size:
                        if current_chunk:
                            current_chunk += " " + word
                        else:
                            current_chunk = word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
            else:
                current_chunk = para
    
    # 마지막 청크 저장
    if current_chunk:
        chunks.append(current_chunk)
    
    # 오버랩 적용 (선택적)
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # 이전 청크의 마지막 부분을 앞에 추가
                prev_suffix = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
                chunk = prev_suffix + " ... " + chunk
            overlapped_chunks.append(chunk)
        return overlapped_chunks
    
    return chunks
