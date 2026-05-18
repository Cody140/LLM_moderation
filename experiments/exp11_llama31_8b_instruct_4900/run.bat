@echo off
REM ===================================================================
REM exp11 — Llama 3.1 8B Instruct (cita modele, v1 promps)
REM
REM Mērķis: salīdzinājums ar exp08 (Qwen 2.5 7B v1 prompt)
REM
REM   1. LM Studio: search "Meta-Llama-3.1-8B-Instruct-GGUF" -> lmstudio-community
REM   2. Lejupielādēt Q4_K_M (~4.9 GB)
REM   3. Load tab: Context=8192, GPU offload=MAX, Concurrent=4, Flash Attention=ON
REM   4. Inference tab:
REM        - System prompt: TUKŠS (kods sūta v1 system caur API)
REM        - Structured Output: ON ar to pašu JSON Schema kā exp08
REM        - Temperature: 0
REM   5. Server: port 1234
REM   6. Pārbaudīt model id: curl http://localhost:1234/v1/models
REM      ja atšķiras no "llama-3.1-8b-instruct" - aizvieto --llm-model parametru
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
    --methods llm ^
    --llm-backend real ^
    --llm-base-url http://localhost:1234 ^
    --llm-endpoint-path /v1/chat/completions ^
    --llm-model llama-3.1-8b-instruct ^
    --llm-prompt-version qwen_civil ^
    --runs 1 --warmup-runs 1 ^
    --llm-timeout-sec 90 ^
    --llm-max-concurrency 4 ^
    --llm-temperature 0.0 ^
    --llm-max-input-chars 1200 ^
    --detailed-results-csv experiments\exp11_llama31_8b_instruct_4900\detailed.csv ^
    --summary-results-csv experiments\exp11_llama31_8b_instruct_4900\summary.csv ^
    --case-type-results-csv experiments\exp11_llama31_8b_instruct_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
