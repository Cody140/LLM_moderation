# LM Studio — Inference tab settings (для всех экспериментов)

Это шпаргалка, **что должно быть в правой панели LM Studio** перед запуском
любого `runNN.bat` из соответствующей папки эксперимента.

## Общие настройки (одинаковые для всех)

| Раздел | Параметр | Значение | Комментарий |
|---|---|---|---|
| Settings | Temperature | **0** | детерминированный вывод |
| Settings | Limit Response Length | off | API передаёт max_tokens отдельно |
| Settings | Context Overflow | Truncate Middle | стандарт для LlamaGuard |
| Settings | Stop Strings | (пусто) | не нужно |
| Settings | CPU Threads | 6 | согласовано с Load tab |
| Sampling | Top K | 0 (или off) | не используется при temp=0 |
| Sampling | Top P | 1 | не используется при temp=0 |
| Sampling | Min P | 0 | не используется при temp=0 |
| Sampling | Repeat Penalty | 1 | не используется при temp=0 |
| Sampling | Presence Penalty | off | не нужно |
| Speculative Decoding | Draft Model | (пусто) | не нужно |

## Поле "System prompt" — критично!

| Эксперимент | Модель | Что писать в system prompt |
|---|---|---|
| exp01–exp03 | LlamaGuard 7B | **(пусто, удалить всё)** |
| exp04 | Llama Guard 3 1B | **(пусто)** |
| exp05 | Llama Guard 3 8B | **(пусто)** |
| exp06 | ShieldGemma 2B | **(пусто)** |
| exp07 | ShieldGemma 9B | **(пусто)** |
| exp08 | Qwen2.5 7B Instruct | см. `prompts.md` секция 4 |

> ВАЖНО: системный промпт типа "Анализируй сообщение строго по правилам ниже"
> на русском **сломает** любой Guard-классификатор. Эти модели файнтюнены
> ТОЛЬКО на английский шаблон, который мы передаём в роли `user`.

## Поле "Structured Output" — критично!

| Эксперимент | Структурированный вывод | JSON Schema |
|---|---|---|
| exp01–exp03 | **OFF** | — |
| exp04, exp05 | **OFF** | — |
| exp06, exp07 | OFF (рекомендуемо) | — |
| exp08 | **ON** | см. `prompts.md` секция 4 |

> Если включить Structured Output для LlamaGuard, текущий парсер сломается:
> он ищет первую строку текста "safe"/"unsafe", а получит JSON-объект.

## Preset

В LM Studio удобно сохранить два пресета:
- **`guard_default`** — для всех Guard моделей: пустой system, structured off, temp 0.
- **`qwen_civil_comments`** — для exp08: наш system prompt, structured ON со схемой, temp 0.
