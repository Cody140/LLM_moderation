@echo off
REM ===================================================================
REM exp06 — ShieldGemma 2B (Yes/No formāts!)
REM   1. LM Studio: search "shieldgemma-2b-GGUF" -> QuantFactory
REM   2. Lejupielādēt Q5_K_M (~1.6 GB)
REM   3. Load tab: Context=8192, GPU offload=MAX, Concurrent=4
REM   4. Inference tab: System prompt TUKŠS, Structured Output OFF, Temp=0
REM   5. Server: port 1234
REM   6. SVARĪGI: kods (LMStudioGuardClient) jāatjaunina:
REM      - šablons pārslēdzas uz ShieldGemma promptu
REM      - _extract_label parse "Yes"/"No"
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model shieldgemma-2b ^
    --llm-prompt-version shieldgemma ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 60 ^
    --llm-max-concurrency 4 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp06_shieldgemma2b_4900\detailed.csv ^
    --summary-results-csv experiments\exp06_shieldgemma2b_4900\summary.csv ^
    --case-type-results-csv experiments\exp06_shieldgemma2b_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
