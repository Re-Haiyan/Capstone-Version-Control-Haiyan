#!/bin/bash
# After queue1 (b, c1, c2): D1 emphasises the marketplace rows (repeated twice per epoch); C1 is repeated with two more seeds to measure run-to-run variation.
cd "$(dirname "$0")/../.."
export PYTHONUTF8=1
PY=D:/defaketive-train/Scripts/python.exe
while [ ! -f research/xlmr_optimization/runs/queue1.done ]; do sleep 30; done
run() { name=$1; seed=$2; shift; shift; $PY research/xlmr_optimization/finetune.py --name "$name" "$@" --epochs 2 --seed $seed > research/xlmr_optimization/runs/$name.log 2>&1; }
run d1_mix_ce_rep2_s1 1 --mix firecs+market --loss ce --market-repeat 2
run c1_mix_ce_s2      2 --mix firecs+market --loss ce
run c1_mix_ce_s3      3 --mix firecs+market --loss ce
echo finished > research/xlmr_optimization/runs/queue3.done
