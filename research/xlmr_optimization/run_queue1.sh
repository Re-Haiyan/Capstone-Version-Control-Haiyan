#!/bin/bash
# Experiments B and C (seed 1, 2 epochs, lr 2e-5), one after another: CPU training uses all 12 threads.
cd "$(dirname "$0")/../.."
export PYTHONUTF8=1
PY=D:/defaketive-train/Scripts/python.exe
run() { name=$1; shift; $PY research/xlmr_optimization/finetune.py --name "$name" "$@" --epochs 2 --seed 1 > research/xlmr_optimization/runs/$name.log 2>&1; }
run b_firecs_s1      --mix firecs
run c1_mix_ce_s1     --mix firecs+market --loss ce
run c2_mix_weighted_s1 --mix firecs+market --loss weighted
echo finished > research/xlmr_optimization/runs/queue1.done
