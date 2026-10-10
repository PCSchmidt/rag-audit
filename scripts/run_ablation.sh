#!/bin/bash
# 2x2 ablation: {small, base} x {no titles, page titles}. Dev freezes each threshold; test runs once on seed 3.
set -e
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python
S=cross-encoder/nli-deberta-v3-small
B=cross-encoder/nli-deberta-v3-base
run() {  # tag model [--titles]
  tag=$1; model=$2; shift 2
  mkdir -p results/ablation/$tag
  $PY scripts/fever_benchmark.py dev --model $model --tag $tag "$@" > results/ablation/$tag/dev.log 2>&1
  $PY scripts/fever_benchmark.py test --model $model --tag $tag --test-seed 3 "$@" > results/ablation/$tag/test.log 2>&1
}
run small_plain $S
run small_titles $S --titles
run base_plain $B
run base_titles $B --titles
echo ALL_DONE > results/ablation/DONE
