# exp11 — Llama 3.1 8B Instruct (rekomendētais)

## Modelis

| Parametrs | Vērtība |
|---|---|
| Nosaukums | Llama 3.1 8B Instruct (GGUF Q4_K_M) |
| LM Studio model id | `llama-3.1-8b-instruct` |
| GGUF avots | https://huggingface.co/lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF |

## Datukopa

code/data/benchmark_sample_4900.csv (N=4900)

## LM Studio parametri

| Parametrs | Vērtība |
|---|---|
| Context Length | 8192 |
| GPU Offload | MAX (32 layers) |
| Max Concurrent Predictions | 4 |
| Flash Attention | ON |
| System prompt | (empty — code injects via API) |
| Structured Output | ON ar JSON Schema {"label": enum, "category": enum} |

## CLI parametri (`benchmark_moderation.py`)

| Parametrs | Vērtība |
|---|---|
| --llm-model | llama-3.1-8b-instruct |
| --llm-prompt-version | qwen_civil |
| --llm-temperature | 0.0 |
| --llm-max-concurrency | 4 |
| --llm-timeout-sec | 90 |

## Promps

```
Tas pats v1 prompts kā exp08. Visi parametri identiski — atšķiras tikai modelis. Sniedz visi labāko balansu: F1=0.805, FPR=0.331.
```
