#!/usr/bin/env bash

# Should be executes from the root of the project 
# Needs ./yelp_data/data relative path to exist 

# A bash pipeline is of form command1 | command2 
# Bash only fails if command2 fails 
# This tells bash to fail if any command fails in the pipeline
set -euo pipefail

INPUT_FILE_PREFIX="./yelp_data/data"
TRIMMED_FILE_PREFIX="${INPUT_FILE_PREFIX}/trimmed/" 
OUTPUT_PATH="${INPUT_FILE_PREFIX}/output/"

cleanup(){
  echo "[INFO] Removing trim files" 
  rm -rf "$TRIMMED_FILE_PREFIX"
  echo "[INFO] Finish removing trim files "
}

on_error(){
  exit_code=$?
  echo "[ERROR] Script failed near line $1 with exit code $exit_code" >&2
  exit "$exit_code"
}

trap 'on_error $LINENO' ERR
trap cleanup EXIT

echo "[INFO] [CHECK] if $INPUT_FILE_PREFIX exists" 
if [[ ! -d "$INPUT_FILE_PREFIX" ]]; then
  echo "[INFO] [START] Fetching data"
  ./yelp_data/get_data.py 
  echo "[INFO] [FINISH] Fetching data"
fi

echo "[INFO] [CHECK] if $TRIMMED_FILE_PREFIX exists" 
if [[ ! -d "$TRIMMED_FILE_PREFIX" ]]; then
  echo "[INFO] Creating output directory: $TRIMMED_FILE_PREFIX"
  mkdir -p "$TRIMMED_FILE_PREFIX"
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "[ERROR] jq is required, but it is not installed or not in PATH." >&2
  exit 1
fi

TRIM_TARGETS_NAMES=(
  "yelp_academic_dataset_review.json review.json 4"
  "yelp_academic_dataset_user.json user.json 4"
)
TRIM_TARGETS=()

for target in "${TRIM_TARGETS_NAMES[@]}"; do
  read -r input_file output_file factor <<< "$target"
  TRIM_TARGETS+=("${INPUT_FILE_PREFIX}/$input_file ${TRIMMED_FILE_PREFIX}/$output_file $factor")
done

for target in "${TRIM_TARGETS[@]}"; do
  read -r input_file output_file factor <<< "$target"

  echo "[INFO][START] Processing $input_file"  

  if [[ ! -f "$input_file" ]]; then
    echo "[ERROR] Missing input file: $input_file" >&2
    exit 1
  fi

  if ! [[ "$factor" =~ ^[1-9][0-9]*$ ]]; then
    echo "[ERROR] Factor must be a positive integer for: $input_file" >&2
    exit 1
  fi

  total_lines=$(wc -l < "$input_file")
  keep_lines=$(( (total_lines + factor - 1) / factor ))

  mkdir -p "$(dirname "$output_file")"
  head -n "$keep_lines" "$input_file" | jq -c . > "$output_file"

  echo "[INFO][FINISH] Processing $input_file"
done

# The order is very important 
# We first move the raw json files 
# So that when moving the trimmed ones 
# They will override the old ones 
echo "[INFO][START] Moving json files" 

mkdir -p "$OUTPUT_PATH"

for file in "$INPUT_FILE_PREFIX"/*.json; do 
  base_name="$(basename "$file" .json)"
  model_name="${base_name##*_}"
  cp "$file" "${OUTPUT_PATH}/${model_name}.json"
done 

for file in "$TRIMMED_FILE_PREFIX"/*.json; do 
  mv "$file" "$OUTPUT_PATH" 
done 

echo "[INFO][FINISH] Moving json files" 
