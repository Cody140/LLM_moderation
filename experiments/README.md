# Eksperimenti

Šī mape satur 11 eksperimentus, kas salīdzina dažādus lokālos LLM
Civil Comments teksta moderācijas uzdevumā.

Katra mape satur:

- `README.md` — modelis, datukopa, parametri, promps
- `run.bat` — palaišanas skripts (Windows)
- `summary.csv` — binārās klasifikācijas rādītāji
- `casetype.csv` — sadalījums pa primary_case_type
- `category_confusion.json` — multiclass confusion (tikai qwen_civil eksperimentiem)

`detailed.csv` failus var pārģenerēt, palaižot atbilstošo `run.bat`.

## Eksperimentu saraksts

| # | Modelis | Promps | F1 | Recall | FPR |
|---|---|---|---|---|---|
| exp01 | LlamaGuard 7B | llamaguard_o6 | 0.044 | 0.023 | 0.006 |
| exp02 | LlamaGuard 7B (obfuskācija) | llamaguard_o6 | 0.065 | 0.033 | — |
| exp03 | LlamaGuard 7B (N=20000) | llamaguard_o6 | classic/hybrid | | |
| exp04 | Llama Guard 3 1B | llamaguard_s13 | 0.531 | 0.375 | 0.227 |
| exp05 | Llama Guard 3 8B | llamaguard_s13 | 0.073 | 0.038 | 0.007 |
| exp06 | ShieldGemma 2B | shieldgemma | FAILED | | |
| exp07 | ShieldGemma 9B | shieldgemma | NOT RUN | | |
| exp08 | Qwen 2.5 7B v1 | qwen_civil | **0.841** | 0.782 | 0.467 |
| exp09 | Qwen 2.5 7B v2 (strict) | qwen_civil_v2 | 0.361 | 0.222 | 0.037 |
| exp10 | Qwen 2.5 7B v3 (balansēts) | qwen_civil_v3 | 0.351 | 0.214 | 0.050 |
| exp11 | **Llama 3.1 8B Instruct** | qwen_civil | 0.805 | 0.710 | **0.331** |

Praktiski rekomendējamais variants: **exp11** — Llama 3.1 8B Instruct ar qwen_civil v1 promptu.

## Datu sagatavošana

Pirms eksperimentu palaišanas:

```bash
# Lejupielādēt Civil Comments no HuggingFace vai Kaggle
huggingface-cli download google/civil_comments --repo-type dataset

# Ģenerēt sabalansētu izlasi
cd ..
python scripts/build_smoke_sample.py \
    --input civil_comments_train.csv \
    --output data/benchmark_sample_4900.csv \
    --total 4900 --per-bucket 700

# Ģenerēt obfuskācijas izlasi (atvasinātu no 4900)
python scripts/build_obfuscated_sample.py \
    --input data/benchmark_sample_4900.csv \
    --output data/obfuscated_sample.csv
```

Tad palaist konkrēto eksperimentu, piem.:

```bash
cd experiments/exp11_llama31_8b_instruct_4900
./run.bat
```
