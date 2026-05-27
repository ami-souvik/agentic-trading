"""
News article deduplication via sentence-transformer cosine similarity.

Uses all-MiniLM-L6-v2 (free, ~80 MB, runs locally) to embed article titles.
Articles with cosine similarity > 0.85 to any already-retained article are dropped.
The model is loaded lazily and cached in the module so repeated calls are cheap.
"""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

_model = None
_SIMILARITY_THRESHOLD = 0.85


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer model (first call only)…")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _cosine_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    normalized = embeddings / norms
    return normalized @ normalized.T


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """
    Remove articles whose title is cosine-similar (> 0.85) to a previously retained article.
    Comparisons are done on `title` field only for speed.
    Returns a deduplicated list preserving original order of first occurrences.
    """
    if len(articles) <= 1:
        return articles

    titles = [a.get("title", "") for a in articles]

    try:
        model = _get_model()
        embeddings = model.encode(titles, batch_size=32, show_progress_bar=False)
    except Exception as e:
        logger.warning("Dedup embedding failed (%s); returning articles without dedup", e)
        return articles

    sim_matrix = _cosine_similarity_matrix(np.array(embeddings))

    kept_indices: list[int] = []
    for i in range(len(articles)):
        is_dup = False
        for j in kept_indices:
            if sim_matrix[i, j] > _SIMILARITY_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            kept_indices.append(i)

    removed = len(articles) - len(kept_indices)
    if removed:
        logger.debug("Dedup removed %d/%d duplicate articles", removed, len(articles))

    return [articles[i] for i in kept_indices]
