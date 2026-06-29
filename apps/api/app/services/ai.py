"""AI service (Claude) — summaries, tags, embeddings, RAG. Degrades gracefully.

Every entry point checks `settings.enable_ai` and the presence of an API key;
when AI is off the portal still works with full-text search and manual metadata.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def ai_enabled() -> bool:
    return settings.enable_ai and bool(settings.anthropic_api_key)


def _client():
    from anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key)


def generate_summary(text: str, max_chars: int = 12000) -> str | None:
    """Produce a concise summary of a report's extracted text."""
    if not ai_enabled():
        return None
    try:
        msg = _client().messages.create(
            model=settings.ai_model,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Summarize this internal engineering report in 3-4 sentences for a "
                        "knowledge-base card. Be concrete about what was built/tested and the "
                        f"key result.\n\n{text[:max_chars]}"
                    ),
                }
            ],
        )
        return msg.content[0].text.strip()
    except Exception as exc:  # pragma: no cover - network
        logger.warning("AI summary failed: %s", exc)
        return None


def generate_tags(text: str, max_chars: int = 12000) -> list[str]:
    """Suggest topical tags for a report."""
    if not ai_enabled():
        return []
    try:
        msg = _client().messages.create(
            model=settings.ai_model,
            max_tokens=120,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Return 5-8 short lowercase topic tags (comma-separated, no #) for this "
                        f"engineering report:\n\n{text[:max_chars]}"
                    ),
                }
            ],
        )
        raw = msg.content[0].text.strip()
        return [t.strip().lower() for t in raw.replace("\n", ",").split(",") if t.strip()][:8]
    except Exception as exc:  # pragma: no cover
        logger.warning("AI tags failed: %s", exc)
        return []


def embed_text(chunks: list[str]) -> list[list[float]] | None:
    """Placeholder embedding hook.

    Wire a real embedding provider here (e.g. Azure OpenAI embeddings or a
    sentence-transformers service). Returns None when unavailable so callers
    skip semantic indexing without error.
    """
    if not ai_enabled():
        return None
    logger.info("embed_text: configure an embedding backend to enable semantic search")
    return None
