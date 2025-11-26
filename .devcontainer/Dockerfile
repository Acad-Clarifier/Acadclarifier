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

# copy repo files into container workspace (devcontainer build context)
WORKDIR /workspaces/acadclarifier-to-vector

# install pip packages (requirements.txt will be copied by Codespaces)
COPY requirements.txt /workspaces/acadclarifier-to-vector/
RUN pip install --upgrade pip && pip install -r requirements.txt

# default command
CMD [ "sleep", "infinity" ]
