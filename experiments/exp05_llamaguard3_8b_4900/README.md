# exp05 — Llama Guard 3 8B

## Modelis

| Parametrs | Vērtība |
|---|---|
| Nosaukums | Llama Guard 3 8B (GGUF Q4_K_M imatrix) |
| LM Studio model id | `llama-guard-3-8b-imat` |
| GGUF avots | https://huggingface.co/bartowski/Meta-Llama-Guard-3-8B-GGUF |

## Datukopa

code/data/benchmark_sample_4900.csv (N=4900)

## LM Studio parametri

| Parametrs | Vērtība |
|---|---|
| Context Length | 4096 |
| GPU Offload | MAX (32 layers) |
| Max Concurrent Predictions | 4 |
| Flash Attention | ON |
| System prompt | (empty) |
| Structured Output | OFF |

## CLI parametri (`benchmark_moderation.py`)

| Parametrs | Vērtība |
|---|---|
| --llm-model | llama-guard-3-8b-imat |
| --llm-prompt-version | llamaguard_s13 |
| --llm-temperature | 0.0 |
| --llm-max-concurrency | 4 |
| --llm-timeout-sec | 90 |

## Promps

```
Tas pats šablons kā exp04 (llamaguard_s13, S1-S13 kategorijas).
```
