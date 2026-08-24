from pathlib import Path

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "md", "markdown"}


def get_file_type(filename: str) -> str:
    """Return the storage category for a supported filename."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension in {"pdf", "docx"}:
        return "documents"
    if extension in {"txt", "md", "markdown"}:
        return "texts"
    raise ValueError(f"Unsupported file type: .{extension or 'none'}")
