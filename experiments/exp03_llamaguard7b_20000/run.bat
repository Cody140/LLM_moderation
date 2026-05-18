@echo off
cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
echo === STEP 1: classic + hybrid (fast) ===
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_20000.csv ^
    --methods classic,hybrid ^
    --llm-backend stub ^
    --runs 1 --warmup-runs 0 ^
    --detailed-results-csv experiments\exp03_llamaguard7b_20000\detailed_classic_hybrid.csv ^
    --summary-results-csv experiments\exp03_llamaguard7b_20000\summary_classic_hybrid.csv ^
    --case-type-results-csv experiments\exp03_llamaguard7b_20000\casetype_classic_hybrid.csv

echo === STEP 2: LLM (LlamaGuard 7B) — UZMANĪBU ~10h ===
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_20000.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-model llamaguard-7b ^
    --runs 1 --warmup-runs 0 ^
    --llm-timeout-sec 60 ^
    --llm-max-concurrency 4 ^
    --detailed-results-csv experiments\exp03_llamaguard7b_20000\detailed_llm.csv ^
    --summary-results-csv experiments\exp03_llamaguard7b_20000\summary_llm.csv ^
    --case-type-results-csv experiments\exp03_llamaguard7b_20000\casetype_llm.csv
pause
