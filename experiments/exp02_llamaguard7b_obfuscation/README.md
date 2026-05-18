# exp02 — LlamaGuard 7B uz obfuscētajiem datiem

## Modelis

| Parametrs | Vērtība |
|---|---|
| Nosaukums | LlamaGuard 7B (GGUF Q4_K_S) |
| LM Studio model id | `llamaguard-7b` |
| GGUF avots | https://huggingface.co/TheBloke/LlamaGuard-7B-GGUF |

## Datukopa

code/data/obfuscated_sample.csv (N=600, 100 × 6 obfuskācijas tipi, visi harmful)

## LM Studio parametri

| Parametrs | Vērtība |
|---|---|
| Context Length | 2048 |
| GPU Offload | MAX (32 layers) |
| Max Concurrent Predictions | 4 |
| Flash Attention | ON |
| System prompt | (empty) |
| Structured Output | OFF |

## CLI parametri (`benchmark_moderation.py`)

| Parametrs | Vērtība |
|---|---|
| --llm-model | llamaguard-7b |
| --llm-prompt-version | llamaguard_o6 |
| --llm-temperature | 0.0 |
| --llm-max-concurrency | 4 |
| --llm-timeout-sec | 60 |

## Promps

```
Tas pats šablons kā exp01 (llamaguard_o6). {text} aizvietots ar obfuscētu Civil Comments rindu.
```
