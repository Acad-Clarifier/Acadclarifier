# base image with Python
FROM mcr.microsoft.com/devcontainers/python:3.11

# avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to the Repo Root inside the container
WORKDIR /workspaces/Acadclarifier

# COPY specific file from the subfolder (relative to the build context)
# Destination is explicit to ensure structure is maintained
COPY to-vector/requirements.txt /workspaces/Acadclarifier/to-vector/

# Install dependencies
# Note: We point to the file we just copied
RUN pip install --upgrade pip && \
    pip install -r /workspaces/Acadclarifier/to-vector/requirements.txt
