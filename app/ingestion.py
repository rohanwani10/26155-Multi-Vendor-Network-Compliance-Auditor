import io
import zipfile


def extract_files(filename: str, content: bytes) -> list[tuple[str, str]]:
    """Return a list of (filename, text) pairs. Unzips content if it's a ZIP
    archive; otherwise treats it as a single config file."""
    if zipfile.is_zipfile(io.BytesIO(content)):
        extracted = []
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                extracted.append((name, zf.read(name).decode("utf-8", errors="replace")))
        return extracted
    return [(filename, content.decode("utf-8", errors="replace"))]
