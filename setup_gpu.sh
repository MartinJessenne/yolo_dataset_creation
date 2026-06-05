#!/bin/bash
# setup_gpu.sh - Bootstraps a clean Python 3.12 environment on the remote GPU container

echo "=== Starting Python 3.12 Setup ==="

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source uv path for current session
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv is already installed."
fi

# 2. Configure the NVIDIA index URL for Isaac Sim/CUDA dependencies
export UV_EXTRA_INDEX_URL=https://pypi.nvidia.com

# 3. Explicitly install Python 3.12 via uv
echo "Downloading Python 3.12..."
uv python install 3.12

# 4. Create virtual environment
echo "Creating Python 3.12 virtual environment at .venv..."
uv venv --python 3.12

# 5. Sync project dependencies from pyproject.toml
echo "Syncing dependencies from pyproject.toml..."
uv sync --python 3.12

echo "=== Setup Complete! ==="
echo "To execute your training scripts under Python 3.12, run:"
echo "uv run python <script_name>.py"
