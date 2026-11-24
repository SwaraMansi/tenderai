import gc
import re
from functools import lru_cache

MODEL_NAME = "BAAI/bge-small-en-v1.5"

@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME, device="cpu")

def chunk_pages(pages, max_chars=1100, overlap=140):
    chunks = []
    step = max_chars - overlap
    for page in pages:
        current, section = "", None
        paragraphs = [p.strip() for p in re.split(r"\n+", page.get("text", "")) if p.strip()]
        for paragraph in paragraphs:
            heading = re.match(r"^((?:\d+\.)+\d*|[A-Z][.)])\s+(.+)$", paragraph)
            if heading:
                section = heading.group(1)
            if len(paragraph) > max_chars:
                if current:
                    chunks.append({"page_number": page["page_number"], "section_number": section, "content": current.strip()})
                    current = ""
                for start in range(0, len(paragraph), step):
                    piece = paragraph[start:start + max_chars]
                    if piece:
                        chunks.append({"page_number": page["page_number"], "section_number": section, "content": piece})
                continue
            if current and len(current) + len(paragraph) + 1 > max_chars:
                chunks.append({"page_number": page["page_number"], "section_number": section, "content": current.strip()})
                current = current[-overlap:] + "\n" + paragraph
            else:
                current = (current + "\n" + paragraph).strip()
        if current:
            chunks.append({"page_number": page["page_number"], "section_number": section, "content": current.strip()})
    return chunks

def embed_texts(texts, batch_size=8):
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False)
    result = vectors.tolist()
    del vectors
    gc.collect()
    return result
