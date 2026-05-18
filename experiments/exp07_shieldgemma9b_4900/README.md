# exp07 — ShieldGemma 9B

## Modelis

| Parametrs | Vērtība |
|---|---|
| Nosaukums | ShieldGemma 9B (GGUF Q4_K_M) |
| LM Studio model id | `shieldgemma-9b` |
| GGUF avots | https://huggingface.co/LiteLLMs/shieldgemma-9b-GGUF |

## Datukopa

code/data/benchmark_sample_4900.csv (N=4900)

## LM Studio parametri

| Parametrs | Vērtība |
|---|---|
| Context Length | 8192 |
| GPU Offload | MAX (42 layers) |
| Max Concurrent Predictions | 2 |
| Flash Attention | ON |
| System prompt | (empty) |
| Structured Output | OFF |

## CLI parametri (`benchmark_moderation.py`)

| Parametrs | Vērtība |
|---|---|
| --llm-model | shieldgemma-9b |
| --llm-prompt-version | shieldgemma |
| --llm-temperature | 0.0 |
| --llm-max-concurrency | 2 |
| --llm-timeout-sec | 90 |

## Promps

```
Tas pats šablons kā exp06 (shieldgemma Yes/No formāts).
```
