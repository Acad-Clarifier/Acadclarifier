import argparse
from typing import Callable, List, Tuple

# Import all stage modules
import tavily_fetch
import filtering
import chunking
import embeddings
import reranking
import compression_v2
import simplifier


# ======================================================
# PIPELINE DEFINITION
# ======================================================

Stage = Tuple[str, Callable]

PIPELINE: List[Stage] = [
    ("tavily_fetch", tavily_fetch.run),
    ("filtering", filtering.run),
    ("chunking", chunking.run),
    ("embeddings", embeddings.run),
    ("reranking", reranking.run),
    ("compression", compression_v2.run),
    ("simplifier", simplifier.run),
]


# ======================================================
# PIPELINE RUNNER
# ======================================================

def run_pipeline(
    query: str,
    start_stage: str | None = None,
) -> str:
    """
    Executes the pipeline sequentially.
    Allows resuming from any stage.
    """

    current_path = None
    started = start_stage is None

    for name, stage_fn in PIPELINE:
        if not started:
            if name == start_stage:
                started = True
            else:
                continue

        print(f"[PIPELINE] Running stage: {name}")

        if name == "tavily_fetch":
            current_path = stage_fn(
                input_path=None,
                query=query
            )
        else:
            current_path = stage_fn(
                input_path=current_path
            )

        if not current_path:
            raise RuntimeError(f"Stage {name} did not return output path")

    return current_path


# ======================================================
# CLI ENTRYPOINT
# ======================================================

def main():
    parser = argparse.ArgumentParser(
        description="Web Retrieval → RAG Pipeline Orchestrator"
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="User query"
    )

    parser.add_argument(
        "--from-stage",
        type=str,
        choices=[name for name, _ in PIPELINE],
        help="Resume pipeline from this stage"
    )

    args = parser.parse_args()

    final_output = run_pipeline(
        query=args.query,
        start_stage=args.from_stage
    )

    print("\n[PIPELINE COMPLETE]")
    print(f"Final output: {final_output}")


if __name__ == "__main__":
    main()

# py pipeline.py --query "What are the features of Next js framework ?"
