@echo off
cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods classic,llm,hybrid ^
    --llm-backend real ^
    --llm-model llamaguard-7b ^
    --runs 1 --warmup-runs 0 ^
    --llm-timeout-sec 60 ^
    --llm-max-concurrency 2 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --llm-endpoint-path /v1/chat/completions ^
    --detailed-results-csv experiments\exp01_llamaguard7b_4900\detailed.csv ^
    --summary-results-csv experiments\exp01_llamaguard7b_4900\summary.csv ^
    --case-type-results-csv experiments\exp01_llamaguard7b_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
