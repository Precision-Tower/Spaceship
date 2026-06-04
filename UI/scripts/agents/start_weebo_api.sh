#!/bin/bash
# Start the local WEEBO Gemma-2B-IT GGUF OpenAI-compatible API server

CONDA_PYTHON="/home/spaztic/miniconda3/envs/weebo_env/bin/python"
MODEL_PATH="/home/spaztic/Core/Dashboard/Models/local/gemma-2b-it.Q4_K_M.gguf"

if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Model file not found at $MODEL_PATH"
    exit 1
fi

echo "Starting WEEBO Local API Server (Gemma-2B-IT GGUF)..."
echo "Host: 127.0.0.1 | Port: 8000 | GPU Layers: 0 (CPU-only)"

exec "$CONDA_PYTHON" -m llama_cpp.server \
  --model "$MODEL_PATH" \
  --n_gpu_layers 0 \
  --host 127.0.0.1 \
  --port 8000 \
  --chat_format gemma
