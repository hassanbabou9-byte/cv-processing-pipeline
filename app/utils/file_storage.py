"""
Local filesystem storage for uploaded CVs and their parsed Markdown.

This is deliberately simple and interim: it saves files to disk under
a generated UUID. Once the database layer exists, upload records will
be tracked there instead (or in addition), and this module may be
replaced with object storage (S3, etc.) — nothing outside this file
should need to change when that happens, since callers only interact
with the functions below, never with raw paths.

No validation or business logic lives here — only "write these bytes
to disk" and "read them back."
"""

import logging
from pathlib import Path

from app.config.settings import Settings
from app.utils.uuid_utils import new_uuid_str

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload(file_bytes: bytes, original_filename: str, settings: Settings) -> tuple[str, Path]:
    """
    Save raw uploaded file bytes to disk under a generated CV id.

    Args:
        file_bytes: Raw file content.
        original_filename: The filename as uploaded (used only to preserve extension).
        settings: Application settings (for the storage directory).

    Returns:
        A tuple of (cv_id, saved_file_path).
    """
    upload_dir = Path(settings.upload_storage_dir)
    _ensure_dir(upload_dir)

    cv_id = new_uuid_str()
    extension = Path(original_filename).suffix.lower()
    saved_path = upload_dir / f"{cv_id}{extension}"

    saved_path.write_bytes(file_bytes)
    logger.info("Saved upload %s -> %s", original_filename, saved_path)

    return cv_id, saved_path


def save_parsed_markdown(cv_id: str, markdown: str, settings: Settings) -> Path:
    """
    Save cleaned Markdown for a given CV id, for later pickup by the
    LLM extraction step (POST /process).

    Args:
        cv_id: The id returned by save_upload().
        markdown: Cleaned Markdown text.
        settings: Application settings (for the storage directory).

    Returns:
        The path the Markdown was saved to.
    """
    parsed_dir = Path(settings.parsed_storage_dir)
    _ensure_dir(parsed_dir)

    saved_path = parsed_dir / f"{cv_id}.md"
    saved_path.write_text(markdown, encoding="utf-8")
    logger.info("Saved parsed markdown for cv_id=%s -> %s", cv_id, saved_path)

    return saved_path


def read_parsed_markdown(cv_id: str, settings: Settings) -> str | None:
    """
    Read back previously saved cleaned Markdown for a CV id.

    Returns:
        The Markdown text, or None if nothing has been saved for this id.
    """
    parsed_path = Path(settings.parsed_storage_dir) / f"{cv_id}.md"
    if not parsed_path.exists():
        return None
    return parsed_path.read_text(encoding="utf-8")