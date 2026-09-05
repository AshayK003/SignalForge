import re
from collections.abc import Generator


def _word_overlap(prev: str, overlap: int) -> str:
    """Trailing words of prev fitting in overlap chars (no mid-word cuts)."""
    if overlap <= 0 or not prev:
        return ""
    words = prev.split()
    out: list[str] = []
    total = 0
    for w in reversed(words):
        add = len(w) + (1 if out else 0)
        if total + add > overlap:
            break
        out.append(w)
        total += add
    if not out and prev:
        # No word boundary fits (e.g. one long token) — char slice beats nothing.
        return prev[-overlap:]
    return " ".join(reversed(out))


def chunk_text(text: str | None, max_chunk_size: int = 3000, overlap: int = 300) -> list[dict]:
    if not text:
        return []

    paragraphs = _split_paragraphs(text)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        sep = 2 if current else 0  # "\n\n" joiner counts toward the budget

        if current_len + sep + para_len <= max_chunk_size:
            current.append(para)
            current_len += sep + para_len
        else:
            if current:
                chunks.append(_make_chunk(chunks, current, overlap))
            current = [para]
            current_len = para_len

            if para_len > max_chunk_size:
                start_idx = len(chunks)
                for _i, sub_chunk in enumerate(_split_large_paragraph(para, max_chunk_size, overlap, start_idx)):
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
        overlap_text = _word_overlap(existing_chunks[-1]["text"], overlap)

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
    current = []
    current_len = 0
    idx = 0
    prev_text = ""

    def _emit() -> dict:
        nonlocal idx, prev_text
        chunk_text_ = " ".join(current)
        prefix = _word_overlap(prev_text, overlap)
        prev_text = chunk_text_
        out = {
            "index": start_index + idx,
            "text": chunk_text_,
            "overlap_prefix": prefix,
            "char_count": len(chunk_text_),
        }
        idx += 1
        return out

    for sent in sentences:
        sent_len = len(sent)
        sep = 1 if current else 0  # " " joiner counts toward the budget
        if current_len + sep + sent_len <= max_size:
            current.append(sent)
            current_len += sep + sent_len
        else:
            if current:
                yield _emit()
            current = [sent]
            current_len = sent_len

    if current:
        yield _emit()
