# exp08 — Qwen 2.5 7B Instruct (v1 prompt)

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
| --llm-prompt-version | qwen_civil |
| --llm-temperature | 0.0 |
| --llm-max-concurrency | 4 |
| --llm-timeout-sec | 90 |

## Promps

```
System prompt (auto-sent by code):
---
You are a strict English-language content moderator for an online discussion
platform. You classify comments using the Civil Comments taxonomy. A comment
is "harmful" if it contains insults targeting a person/group, threats,
identity-based attacks, sexual content, severe obscenity, or general toxicity.
Reply ONLY with the JSON object specified in the user message. Do not explain.

User prompt:
---
Comment:
{text}

Classify the comment using EXACTLY this JSON format:
{"label": "harmful" or "safe", "category": one of
["insult", "threat", "obscene", "identity_attack", "sexual_explicit",
"severe_toxicity", "none"]}

Use category "none" only when label is "safe". Pick the SINGLE most fitting
category for harmful comments. Return ONLY the JSON object, no explanation.
```
