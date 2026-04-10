from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

try:
    from . import sqlite_compat  # noqa: F401
except ImportError:
    import sqlite_compat  # type: ignore # noqa: F401


def _orchestrator_file_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "services"
        / "retrieval-local"
        / "scripts"
        / "runtime_orchestrator.py"
    )


@lru_cache(maxsize=1)
def _load_orchestrator_module() -> ModuleType:
    module_path = _orchestrator_file_path()
    if not module_path.exists():
        raise FileNotFoundError(
            f"Runtime orchestrator not found: {module_path}")

    scripts_dir = str(module_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location(
        "runtime_orchestrator", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load orchestrator module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_local_retrieval_pipeline(**kwargs):
    orchestrator = _load_orchestrator_module()
    return orchestrator.run_local_retrieval_pipeline(**kwargs)
