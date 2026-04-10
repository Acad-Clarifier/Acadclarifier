from __future__ import annotations

import logging
import sys


logger = logging.getLogger(__name__)


def patch_sqlite() -> bool:
    """Patch sqlite3 with pysqlite3 when available for Chroma compatibility."""
    try:
        import pysqlite3 as sqlite3  # type: ignore

        sys.modules["sqlite3"] = sqlite3
        return True
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        logger.debug("pysqlite3 patch unavailable: %s", exc)
        return False


PATCHED = patch_sqlite()
