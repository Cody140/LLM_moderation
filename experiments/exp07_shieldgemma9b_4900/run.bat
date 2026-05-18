@echo off
REM ===================================================================
REM exp07 — ShieldGemma 9B (Yes/No formāts, tāds pats kā exp06)
REM   1. LM Studio: search "shieldgemma-9b-GGUF" -> LiteLLMs vai mradermacher
REM   2. Lejupielādēt Q4_K_M (~5.4 GB)
REM   3. Load tab: Context=8192, GPU offload=MAX, Concurrent=2
REM   4. Inference tab: System prompt TUKŠS, Structured Output OFF
REM   5. Server: port 1234
REM   6. Kods jau atjaunināts ar Yes/No parser (pēc exp06)
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model shieldgemma-9b ^
    --llm-prompt-version shieldgemma ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 90 ^
    --llm-max-concurrency 2 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp07_shieldgemma9b_4900\detailed.csv ^
    --summary-results-csv experiments\exp07_shieldgemma9b_4900\summary.csv ^
    --case-type-results-csv experiments\exp07_shieldgemma9b_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
