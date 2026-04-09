from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType


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
