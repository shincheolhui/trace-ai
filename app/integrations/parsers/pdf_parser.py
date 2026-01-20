# app/integrations/parsers/pdf_parser.py
"""PDF 파일 파싱 (pdfplumber 기반)"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import List, Optional

import pdfplumber

from app.integrations.parsers.text_parser import chunk_text

logger = logging.getLogger(__name__)


def parse_pdf_file(file_path: Path) -> str:
    """PDF 파일에서 텍스트 추출
    
    Args:
        file_path: PDF 파일 경로
        
    Returns:
        추출된 텍스트
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            texts = []
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
                    logger.debug(f"[pdf_parser] Page {i+1}: {len(page_text)} chars")
            
            full_text = "\n\n".join(texts)
            logger.info(f"[pdf_parser] Parsed {file_path.name}: {len(pdf.pages)} pages, {len(full_text)} chars")
            return full_text
    except Exception as e:
        logger.error(f"[pdf_parser] Failed to parse {file_path.name}: {e}")
        raise


def parse_pdf_bytes(content: bytes, filename: str = "unknown.pdf") -> str:
    """PDF 바이트 데이터에서 텍스트 추출
    
    Args:
        content: PDF 파일 바이트 내용
        filename: 파일명 (로깅용)
        
    Returns:
        추출된 텍스트
    """
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            texts = []
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
            
            full_text = "\n\n".join(texts)
            logger.info(f"[pdf_parser] Parsed {filename}: {len(pdf.pages)} pages, {len(full_text)} chars")
            return full_text
    except Exception as e:
        logger.error(f"[pdf_parser] Failed to parse {filename}: {e}")
        raise


def extract_pdf_metadata(file_path: Path) -> dict:
    """PDF 메타데이터 추출
    
    Args:
        file_path: PDF 파일 경로
        
    Returns:
        메타데이터 딕셔너리
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            metadata = pdf.metadata or {}
            return {
                "title": metadata.get("Title", ""),
                "author": metadata.get("Author", ""),
                "subject": metadata.get("Subject", ""),
                "creator": metadata.get("Creator", ""),
                "producer": metadata.get("Producer", ""),
                "page_count": len(pdf.pages),
            }
    except Exception as e:
        logger.warning(f"[pdf_parser] Failed to extract metadata from {file_path.name}: {e}")
        return {}


def extract_pdf_metadata_bytes(content: bytes) -> dict:
    """PDF 바이트에서 메타데이터 추출"""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            metadata = pdf.metadata or {}
            return {
                "title": metadata.get("Title", ""),
                "author": metadata.get("Author", ""),
                "subject": metadata.get("Subject", ""),
                "creator": metadata.get("Creator", ""),
                "producer": metadata.get("Producer", ""),
                "page_count": len(pdf.pages),
            }
    except Exception as e:
        logger.warning(f"[pdf_parser] Failed to extract metadata: {e}")
        return {}
