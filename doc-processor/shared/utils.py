"""
Utility functions for Docling document processing
"""

import os
import hashlib
from typing import Dict, Any, List
from pathlib import Path


def get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)


def detect_format(file_path: str) -> str:
    """Detect document format from file extension"""
    suffix = Path(file_path).suffix.lower()
    format_map = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc',
        '.pptx': 'pptx',
        '.ppt': 'ppt',
        '.xlsx': 'xlsx',
        '.html': 'html',
        '.htm': 'html',
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.tiff': 'image',
        '.tif': 'image',
    }
    return format_map.get(suffix, 'unknown')


def validate_file_size(file_path: str, max_size: int) -> bool:
    """Validate file size against maximum"""
    return get_file_size(file_path) <= max_size


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Chunk text into smaller pieces for RAG

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries with text and metadata
    """
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        chunks.append({
            'text': chunk_text,
            'metadata': {
                'chunk_index': chunk_index,
                'start_char': start,
                'end_char': end,
                'chunk_type': 'text'
            }
        })

        start = end - chunk_overlap
        chunk_index += 1

    return chunks
