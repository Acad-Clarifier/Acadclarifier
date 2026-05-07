# # extract_bundle.py

# One time script for extracting .tar.gz file in modal


import modal

app = modal.App("extract-chroma")

volume = modal.Volume.from_name(
    "acadclarifier-local",
    create_if_missing=False
)

image = modal.Image.debian_slim().pip_install("tarfile")


@app.function(
    volumes={"/modal/vol": volume},
    timeout=600
)
def extract():
    import tarfile
    import os

    tar_path = "/modal/vol/data/local"
    extract_path = "/modal/vol/data/extracted"

    os.makedirs(extract_path, exist_ok=True)

    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_path)

    print("Extraction complete.")


@app.local_entrypoint()
def main():
    extract.remote()


# DEBUG SCRIPT BELOW. DONT UNCOMMENT

# @app.function(volumes={"/modal/vol": volume})
# def debug_path():
#     import os
#     print("Listing files in /modal/vol:")
#     for root, dirs, files in os.walk("/modal/vol"):
#         for name in files:
#             print(os.path.join(root, name))
