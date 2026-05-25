@echo off
cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\obfuscated_sample.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model qwen2.5-7b-instruct ^
    --llm-prompt-version qwen_civil ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 90 ^
    --llm-max-concurrency 4 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp12_qwen25_7b_obfuscation\detailed.csv ^
    --summary-results-csv experiments\exp12_qwen25_7b_obfuscation\summary.csv ^
    --case-type-results-csv experiments\exp12_qwen25_7b_obfuscation\casetype.csv

echo EXIT_CODE=%ERRORLEVEL%
pause