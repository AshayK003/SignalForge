import re
from typing import Generator


def chunk_text(text: str | None, max_chunk_size: int = 3000, overlap: int = 300) -> list[dict]:
    if not text:
        return []

    paragraphs = _split_paragraphs(text)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        if current_len + para_len <= max_chunk_size:
            current.append(para)
            current_len += para_len
        else:
            if current:
                chunks.append(_make_chunk(chunks, current, overlap))
            current = [para]
            current_len = para_len

            if para_len > max_chunk_size:
                start_idx = len(chunks)
                for i, sub_chunk in enumerate(_split_large_paragraph(para, max_chunk_size, overlap, start_idx)):
                    chunks.append(sub_chunk)
                current = []
                current_len = 0

    if current:
        chunks.append(_make_chunk(chunks, current, overlap))

    return chunks


def _make_chunk(existing_chunks: list, paragraphs: list[str], overlap: int) -> dict:
    text = "\n\n".join(paragraphs)
    overlap_text = ""

    if existing_chunks and overlap > 0:
        prev = existing_chunks[-1]["text"]
        overlap_text = prev[-overlap:] if len(prev) > overlap else prev

    return {
        "index": len(existing_chunks),
        "text": text,
        "overlap_prefix": overlap_text,
        "char_count": len(text),
    }


def _split_paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", text)
    return [p.strip() for p in raw if p.strip()]


def _split_large_paragraph(text: str, max_size: int, overlap: int, start_index: int = 0) -> Generator[dict, None, None]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    current_len = 0
    idx = 0

    for sent in sentences:
        sent_len = len(sent)
        if current_len + sent_len <= max_size:
            current.append(sent)
            current_len += sent_len
        else:
            if current:
                chunk_text = " ".join(current)
                yield {"index": start_index + idx, "text": chunk_text, "overlap_prefix": "", "char_count": len(chunk_text)}
                idx += 1
            current = [sent]
            current_len = sent_len

    if current:
        chunk_text = " ".join(current)
        yield {"index": start_index + idx, "text": chunk_text, "overlap_prefix": "", "char_count": len(chunk_text)}
