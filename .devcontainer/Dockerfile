# Dev Container image: Python base plus the toolchains for the other
# five template languages (TypeScript, Kotlin, Rust, Go, C++).
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    nodejs \
    npm \
    golang \
    openjdk-21-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

# uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Rust toolchain
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

# Create a non-root user for development
RUN useradd -m -s /bin/bash vscode
USER vscode
WORKDIR /app

ENV PATH="/app/python/.venv/bin:$PATH"

CMD ["/bin/bash"]
