@echo off
REM ===================================================================
REM exp09 — Qwen2.5 7B Instruct ar UZLABOTU promptu (v2)
REM
REM   1. LM Studio: tas pats Qwen2.5 7B Instruct Q4_K_M kā exp08
REM   2. Load tab: Context=8192, GPU offload=MAX, Concurrent=4, Flash Attention=ON
REM   3. Inference tab:
REM        - System prompt: TUKŠS (kods sūta v2 system caur API)
REM        - Structured Output: ON ar to pašu JSON Schema kā exp08
REM        - Temperature: 0
REM   4. Server: port 1234
REM   5. Kods jau atbalsta --llm-prompt-version qwen_civil_v2
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model qwen2.5-7b-instruct ^
    --llm-prompt-version qwen_civil_v2 ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 90 ^
    --llm-max-concurrency 4 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp09_qwen25_7b_4900_v2\detailed.csv ^
    --summary-results-csv experiments\exp09_qwen25_7b_4900_v2\summary.csv ^
    --case-type-results-csv experiments\exp09_qwen25_7b_4900_v2\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
