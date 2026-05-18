# exp09 — Qwen 2.5 7B Instruct (v2 strict)

## Modelis

| Parametrs | Vērtība |
|---|---|
| Nosaukums | Qwen 2.5 7B Instruct (GGUF Q4_K_M) |
| LM Studio model id | `qwen2.5-7b-instruct` |
| GGUF avots | https://huggingface.co/lmstudio-community/Qwen2.5-7B-Instruct-GGUF |

## Datukopa

code/data/benchmark_sample_4900.csv (N=4900)

## LM Studio parametri

| Parametrs | Vērtība |
|---|---|
| Context Length | 8192 |
| GPU Offload | MAX (28 layers) |
| Max Concurrent Predictions | 4 |
| Flash Attention | ON |
| System prompt | (empty — code injects via API) |
| Structured Output | ON ar JSON Schema {"label": enum, "category": enum} |

## CLI parametri (`benchmark_moderation.py`)

| Parametrs | Vērtība |
|---|---|
| --llm-model | qwen2.5-7b-instruct |
| --llm-prompt-version | qwen_civil_v2 |
| --llm-temperature | 0.0 |
| --llm-max-concurrency | 4 |
| --llm-timeout-sec | 90 |

## Promps

```
Stingrāks variants — pievienota "lean toward safe" instrukcija un priority hierarhija.
Pilns teksts: benchmark_moderation.py → _QWEN_V2_SYSTEM un _QWEN_CIVIL_V2_TEMPLATE.
```
