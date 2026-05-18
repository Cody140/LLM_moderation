# Lokālo lielo valodas modeļu pielietojums teksta moderācijā

Bakalaura darba kods un eksperimenti.

**Autors:** Romans Drozdovs (RTU, 2026)
**Tēma:** Lokālo lielo valodas modeļu pielietojums lingvistiskās filtrēšanas un klasifikācijas uzdevumos

## Apraksts

Šis repozitorijs satur Python implementāciju trīs teksta moderācijas pieejām un to salīdzinošo bencmarku uz Civil Comments datu kopuma:

- **Classic** — noteikumos balstīta moderācija (atslēgvārdi, regulārās izteiksmes)
- **LLM** — lokāli palaists LLM caur LM Studio (LlamaGuard 7B, Llama Guard 3 1B/8B, ShieldGemma 2B/9B, Qwen 2.5 7B, Llama 3.1 8B)
- **Hybrid** — classic + LLM fallback uz `uncertain` gadījumiem

## Repozitorija struktūra

```
.
├── app/                          # Moderatoru implementācijas (FastAPI scaffolding)
│   ├── moderators/
│   │   ├── classic.py            # Classic moderators
│   │   ├── llm.py                # LLM moderators
│   │   └── hybrid.py             # Hybrid moderators
│   ├── services/                 # llm_client, moderation_service, job_store
│   ├── api/                      # API routes
│   └── workers/                  # Queue worker
├── scripts/                      # Datu sagatavošanas skripti
│   ├── build_smoke_sample.py     # Sabalansētas izlases ģenerēšana
│   ├── build_obfuscated_sample.py # Obfuskācijas variantu ģenerēšana
│   ├── check_lmstudio.py         # LM Studio sasniedzamības pārbaude
│   └── debug_errors.py
├── data/                         # Bencmarka izlases (ievietot .csv šeit)
├── experiments/                  # 11 eksperimentu mapes
│   ├── exp01_llamaguard7b_4900/
│   │   ├── README.md
│   │   ├── run.bat
│   │   ├── summary.csv
│   │   └── casetype.csv
│   ├── exp04_llamaguard3_1b_4900/
│   ├── ...
│   ├── exp11_llama31_8b_instruct_4900/
│   └── _charts/                  # Matplotlib grafiki
├── tests/                        # Unit testi
├── benchmark_moderation.py       # Galvenais bencmarka skripts (6 promptu versijas)
├── benchmark_moderation_methods.md
├── benchmark_moderation_parameters.md
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Atkarības

```
python>=3.10
httpx
fastapi
pydantic
matplotlib
pandas
```

Instalēt:

```bash
pip install -r requirements.txt
```

## Datu kopa

Tiek izmantots **Civil Comments** datu kopums no Google Jigsaw (~1.8M rindas).

Lejupielādēt no HuggingFace:

```
huggingface-cli download google/civil_comments --repo-type dataset
```

Vai no Kaggle: <https://www.kaggle.com/c/jigsaw-unintended-bias-in-toxicity-classification>

Saglabāt `civil_comments_train.csv` repozitorija saknes mapē, tad ģenerēt izlases:

```bash
cd .
python scripts/build_smoke_sample.py --input civil_comments_train.csv \
    --output data/benchmark_sample_4900.csv --total 4900 --per-bucket 700
python scripts/build_obfuscated_sample.py \
    --input data/benchmark_sample_4900.csv --output data/obfuscated_sample.csv
```

## LM Studio sagatavošana

Lejupielādēt vajadzīgos GGUF modeļus LM Studio sadaļā **Discover**. Pilns saraksts pieejams `experiments/_prompts/prompts.md`.

Iesāktie modeļi:

- `lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF` (rekomendēts)
- `lmstudio-community/Qwen2.5-7B-Instruct-GGUF`
- `MaziyarPanahi/Llama-Guard-3-1B-GGUF`

Palaist LM Studio servera režīmā uz porta 1234. Inference tab uzstādīt:

- Temperature: 0
- Structured Output: ON (Qwen, Llama 3.1) ar JSON Schema `{label, category}`
- System prompt: tukšs (Guard modeļiem)

## Bencmarka palaišana

```bash
python benchmark_moderation.py \
    --texts-csv data/benchmark_sample_4900.csv \
    --methods llm \
    --llm-backend real \
    --llm-model llama-3.1-8b-instruct \
    --llm-prompt-version qwen_civil \
    --runs 1 --warmup-runs 1 \
    --llm-temperature 0.0 \
    --detailed-results-csv experiments/exp11_llama31_8b_instruct_4900/detailed.csv \
    --summary-results-csv experiments/exp11_llama31_8b_instruct_4900/summary.csv \
    --case-type-results-csv experiments/exp11_llama31_8b_instruct_4900/casetype.csv
```

Vai vienkārši palaist atbilstošo `run.bat` no `experiments/expNN_*/` mapes.

## Eksperimentu pārskats

| # | Modelis | F1 | Recall | FPR |
|---|---|---|---|---|
| exp01 | LlamaGuard 7B | 0.044 | 0.023 | 0.006 |
| exp04 | Llama Guard 3 1B | 0.531 | 0.375 | 0.227 |
| exp05 | Llama Guard 3 8B | 0.073 | 0.038 | 0.007 |
| exp08 | Qwen 2.5 7B v1 | **0.841** | 0.782 | 0.467 |
| exp09 | Qwen 2.5 7B v2 (strict) | 0.361 | 0.222 | 0.037 |
| exp10 | Qwen 2.5 7B v3 (balanced) | 0.351 | 0.214 | 0.050 |
| exp11 | **Llama 3.1 8B Instruct** | 0.805 | 0.710 | **0.331** |

Praktiski rekomendējamais risinājums: **exp11** (Llama 3.1 8B Instruct ar v1 promptu) — labākais Recall/FPR kompromiss.

## Licence

MIT — skat. LICENSE failu.
