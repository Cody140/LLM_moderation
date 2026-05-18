@echo off
REM ===================================================================
REM exp04 — Llama Guard 3 1B
REM
REM PIRMS PALAISTŠANAS:
REM   1. LM Studio: search "Llama-Guard-3-1B-GGUF" -> MaziyarPanahi
REM   2. Lejupielādēt Q5_K_M (~1 GB)
REM   3. Load tab: Context=4096, GPU offload=MAX, Concurrent=8, Flash Attention=ON
REM   4. Inference tab: System prompt TUKŠS, Structured Output OFF, Temp=0
REM   5. Server: port 1234
REM   6. Pārbaudīt model id: curl http://localhost:1234/v1/models
REM   7. Kods (LMStudioGuardClient) atjaunināts ar S1-S13 šablonu
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model llama-guard-3-1b ^
    --llm-prompt-version llamaguard_s13 ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 60 ^
    --llm-max-concurrency 8 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp04_llamaguard3_1b_4900\detailed.csv ^
    --summary-results-csv experiments\exp04_llamaguard3_1b_4900\summary.csv ^
    --case-type-results-csv experiments\exp04_llamaguard3_1b_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
