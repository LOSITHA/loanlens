"""Remember what the AI reader returned for a piece of text, so the same text never costs a second AI call."""
import hashlib
import json
import os
import tempfile


def text_key(text):
    """Same key for the same words, whatever the spacing or capital letters."""
    return hashlib.sha256(" ".join(text.split()).lower().encode("utf-8")).hexdigest()


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(path, text):
    """Saved fields for this text, or None."""
    return _load(path).get(text_key(text))


def put(path, text, fields):
    """Save fields for this text. Never raises: a cache that cannot save is just a cache that is empty."""
    try:
        data = _load(path)
        data[text_key(text)] = fields
        folder = os.path.dirname(path) or "."
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError):
        pass
