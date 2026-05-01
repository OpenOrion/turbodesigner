import pickle
from pathlib import Path
from cachetools import LRUCache
from turbodesigner.cli.state import get_workspace_dir


def _get_cache_file() -> Path:
    return get_workspace_dir() / "tessellation.pkl"

_tessellation_cache: LRUCache | None = None


def get_tessellation_cache(maxsize: int = 256) -> LRUCache:
    """Lazily load or create the tessellation LRU cache."""
    global _tessellation_cache
    if _tessellation_cache is not None:
        return _tessellation_cache

    cache_file = _get_cache_file()
    if cache_file.exists():
        try:
            with open(cache_file, "rb") as f:
                _tessellation_cache = pickle.load(f)
            # Resize if needed
            if _tessellation_cache.maxsize != maxsize:
                _tessellation_cache = LRUCache(maxsize=maxsize)
        except Exception:
            _tessellation_cache = LRUCache(maxsize=maxsize)
    else:
        _tessellation_cache = LRUCache(maxsize=maxsize)

    return _tessellation_cache


def save_tessellation_cache() -> None:
    """Persist the cache to disk."""
    if _tessellation_cache is None:
        return
    cache_file = _get_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(_tessellation_cache, f)
