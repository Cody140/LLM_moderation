@echo off
cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\obfuscated_sample.csv ^
    --methods classic,llm,hybrid ^
    --llm-backend real ^
    --llm-model llamaguard-7b ^
    --runs 1 --warmup-runs 0 ^
    --llm-timeout-sec 60 ^
    --llm-max-concurrency 4 ^
    --llm-temperature 0.0 ^
    --detailed-results-csv experiments\exp02_llamaguard7b_obfuscation\detailed.csv ^
    --summary-results-csv experiments\exp02_llamaguard7b_obfuscation\summary.csv ^
    --case-type-results-csv experiments\exp02_llamaguard7b_obfuscation\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
