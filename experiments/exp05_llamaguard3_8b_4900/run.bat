@echo off
REM ===================================================================
REM exp05 — Llama Guard 3 8B
REM   1. LM Studio: search "Llama-Guard-3-8B-GGUF" -> bartowski
REM   2. Lejupielādēt Q4_K_M (~4.9 GB)
REM   3. Load tab: Context=4096, GPU offload=MAX, Concurrent=4
REM   4. Inference tab: System prompt TUKŠS, Structured Output OFF
REM   5. Server: port 1234
REM   6. Kods atjaunināts ar S1-S13 šablonu (vienreiz pirms exp04)
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model llama-guard-3-8b-imat ^
    --llm-prompt-version llamaguard_s13 ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 90 ^
    --llm-max-concurrency 4 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp05_llamaguard3_8b_4900\detailed.csv ^
    --summary-results-csv experiments\exp05_llamaguard3_8b_4900\summary.csv ^
    --case-type-results-csv experiments\exp05_llamaguard3_8b_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
