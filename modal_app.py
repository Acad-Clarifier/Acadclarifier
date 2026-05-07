# modal_app.py

import modal

app = modal.App("acadclarifier-backend")

volume = modal.Volume.from_name(
    "acadclarifier-local",
    create_if_missing=False
)

image = (
    modal.Image.debian_slim()
    .pip_install_from_requirements(
        "requirements.txt"
    )
    .add_local_dir(".", remote_path="/root/project", ignore=[".git"])
)


@app.function(
    image=image,
    volumes={"/modal/vol": volume},
    secrets=[
        modal.Secret.from_name("acadclarifier-secrets")
    ],
    cpu=1,
    memory=2048,
    timeout=600,
)
@modal.concurrent(max_inputs=20)
@modal.wsgi_app()
def flask_app():

    import os
    import sys

    project_root = "/root/project"
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Default to Modal-mounted paths when not explicitly provided via secrets.
    os.environ.setdefault("LOCAL_CHROMA_PATH", "/modal/vol/data/extracted")
    os.environ.setdefault(
        "BOOK_RECOMMENDER_CHROMA_PATH", "/modal/vol/book_recommendation")

    from apps.backend.server import create_app

    return create_app()
