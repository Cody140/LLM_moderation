@echo off
REM ===================================================================
REM exp08 — Qwen2.5 7B Instruct (vispārējs LLM ar custom prompt + JSON Schema)
REM
REM   1. LM Studio: search "Qwen2.5-7B-Instruct-GGUF" -> lmstudio-community
REM   2. Lejupielādēt Q4_K_M (~4.7 GB)
REM   3. Load tab: Context=8192, GPU offload=MAX, Concurrent=4
REM   4. Inference tab:
REM        - System prompt: AIZPILDĪT ar tekstu no README.md sadaļas C
REM        - Structured Output: ON
REM        - JSON Schema: { "type":"object", "properties":{"label":{"type":"string","enum":["harmful","safe"]}}, "required":["label"]}
REM        - Temperature: 0
REM   5. Server: port 1234
REM   6. SVARĪGI: kods atjaunināts:
REM        - User-prompt šablons: "Comment:\n{text}\n\nClassify as 'harmful' or 'safe'."
REM        - _extract_label parse JSON {"label":...}
REM ===================================================================

cd /d "C:\Users\Cody\Desktop\bakalaura darbs\code"
python benchmark_moderation.py ^
    --texts-csv data\benchmark_sample_4900.csv ^
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
    --detailed-results-csv experiments\exp08_qwen25_7b_4900\detailed.csv ^
    --summary-results-csv experiments\exp08_qwen25_7b_4900\summary.csv ^
    --case-type-results-csv experiments\exp08_qwen25_7b_4900\casetype.csv
echo EXIT_CODE=%ERRORLEVEL%
pause
