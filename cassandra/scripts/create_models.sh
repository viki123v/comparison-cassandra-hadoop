#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASSANDRA_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$CASSANDRA_ROOT/.." && pwd)"

JSON_SCHEMA_INPUT_PATH="$PROJECT_ROOT/yelp_data/data/output"
ASSETS_PATH="$CASSANDRA_ROOT/assets"
YELP_PY_MODELS_PATH="$CASSANDRA_ROOT/src/cassandra/models/yelp"

echo "[INFO][CHECK] uv exists"
if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] uv is required. Please install uv before running this script." >&2
    exit 1
fi

echo "[INFO][CHECK] genson exists"
if ! uv run genson --help >/dev/null 2>&1; then
    echo "[ERROR] genson is required. Please install it with: uv add genson" >&2
    exit 1
fi

echo "[INFO][CHECK] datamodel-codegen is installed as a uv tool"
if ! uv tool list | grep -q "datamodel-code-generator"; then
    echo "[ERROR] datamodel-codegen is required as a uv tool. Please install it with: uv tool install datamodel-code-generator" >&2
    exit 1
fi
if ! command -v datamodel-codegen >/dev/null 2>&1; then
    echo "[ERROR] datamodel-codegen is installed as a uv tool, but its executable is not on PATH. Please run: uv tool update-shell" >&2
    exit 1
fi

echo "[INFO][CHECK] $JSON_SCHEMA_INPUT_PATH exists"
if [[ ! -d "$JSON_SCHEMA_INPUT_PATH" ]]; then
    echo "[INFO] Running trim.sh" 

    cd "$PROJECT_ROOT"
    source shared/trim.sh

    echo "[INFO] Finished running trim.sh"
fi

echo "[INFO][CHECK] $ASSETS_PATH exists"
if [[ ! -d "$ASSETS_PATH" ]]; then
    echo "[INFO] Creating assets directory: $ASSETS_PATH"
    mkdir -p "$ASSETS_PATH"
fi

echo "[INFO][CHECK] $YELP_PY_MODELS_PATH exists"
if [[ ! -d "$YELP_PY_MODELS_PATH" ]]; then
    echo "[INFO] Creating Yelp Python models directory: $YELP_PY_MODELS_PATH"
    mkdir -p "$YELP_PY_MODELS_PATH"
fi

echo '[INFO] [START] Creating schemas'
for file in "$JSON_SCHEMA_INPUT_PATH"/*.json; do
    file_name="$(basename "$file")"
    uv run genson "$file" > "${ASSETS_PATH}/${file_name}"
done 
echo '[INFO] [FINISH] Creating schemas'

echo "[INFO] [START] Creating Python models"
for schema in "$ASSETS_PATH"/*.json; do 
    model_name="$(basename "$schema" .json)"
    class_name="${model_name^}"
    datamodel-codegen \
        --input "$schema" \
        --input-file-type jsonschema \
        --output-model-type msgspec.Struct \
        --target-python-version 3.13 \
        --class-name "$class_name" \
        --output "${YELP_PY_MODELS_PATH}/${model_name}.py"
done 
echo "[INFO] [FINISH] Creating Python models"


echo "[INFO] [START] Add __init__.py" 
cd $YELP_PY_MODELS_PATH 
touch __init__.py 

# Add __init__.py in models/ 
# So that from models.yelp is possible 
cd ../
touch __init__.py 
echo "[INFO] [FINISH] Add __init__.py" 