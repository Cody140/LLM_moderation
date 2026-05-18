# benchmark_moderation.py - параметры запуска

Этот файл содержит полный справочник по параметрам запуска скрипта benchmark_moderation.py.

## Базовый запуск

Запуск из папки code:

```powershell
python benchmark_moderation.py
```

## Все параметры

### Источник текста и выборка

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| --text | str | You are an idiot!!! | Текст для режима, когда CSV не используется. Этот текст дублируется count раз. |
| --texts-csv | str | None | Путь к CSV-файлу с текстами. Если задан, используется вместо --text. |
| --text-column | str | text | Имя колонки с текстом в CSV. |
| --label-column | str | None | Опциональная колонка с числовой меткой для расчета качества (accuracy, precision, recall, f1). |
| --label-threshold | float | 0.5 | Порог бинаризации метки: label >= threshold считается токсичным классом (1). |
| --sample-strategy | first или random | first | Стратегия выбора count строк из CSV: первые или случайные. |
| --sample-seed | int | 42 | Seed для случайной выборки при sample-strategy=random. |
| --count | int | 1000 | Размер батча, сколько сообщений отправить на модерацию за один прогон. |

### Методы и количество прогонов

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| --methods | str | classic,ml,hybrid | Список методов через запятую: classic, ml, hybrid. |
| --warmup-runs | int | 1 | Количество прогревочных прогонов на метод (не попадают в итоговые метрики). |
| --runs | int | 5 | Количество измеряемых прогонов на метод. |

### Настройки ML backend

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| --ml-backend | stub или real | stub | Источник для ML-модератора: stub (локальный заглушечный клиент) или real (внешний endpoint). |
| --stub-latency-ms | float | 0.0 | Искусственная задержка на одно сообщение в stub-режиме. |

### Настройки real LLM backend

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| --llm-base-url | str | http://localhost:1234 | Базовый URL внешнего LLM-сервиса. |
| --llm-endpoint-path | str | /api/v1/chat | Путь endpoint для запросов moderation/chat. |
| --llm-model | str | llamaguard-7b | Имя модели, передаваемое в запросе. |
| --llm-auth-token | str | значение LM_API_TOKEN или None | Bearer-токен авторизации. |
| --llm-timeout-sec | float | 30.0 | Таймаут одного HTTP-запроса в секундах. |
| --llm-context-length | int | 2000 | Параметр context_length, отправляемый в backend. |
| --llm-max-input-chars | int | 1200 | Максимальная длина текста, отправляемая в backend. Текст обрезается до этого лимита. |
| --llm-temperature | float | 0.0 | Параметр temperature для LLM-запроса. |
| --llm-max-concurrency | int | 2 | Максимум параллельных запросов к real backend. |

### Выгрузка результатов

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| --output-csv | str | None | Путь для сохранения результатов прогонов в CSV. |

## Ограничения и валидация

Скрипт завершится ошибкой, если:

- count <= 0
- runs <= 0
- warmup-runs < 0
- llm-max-input-chars <= 0
- methods содержит неизвестные значения
- CSV не найден, пустой, либо в нем нет нужных колонок/достаточного числа строк

## Примеры запуска

### 1) Простой локальный тест (stub)

```powershell
python benchmark_moderation.py --methods classic,ml,hybrid --count 1000 --runs 5 --ml-backend stub
```

### 2) CSV с метками + quality метрики

```powershell
python benchmark_moderation.py --texts-csv civil_comments_train.csv --text-column text --label-column toxicity --label-threshold 0.5 --sample-strategy random --sample-seed 42 --count 500 --methods classic,ml,hybrid --runs 3
```

### 3) Real backend (LM Studio)

```powershell
python benchmark_moderation.py --ml-backend real --methods ml,hybrid --count 300 --runs 3 --llm-base-url http://localhost:1234 --llm-endpoint-path /api/v1/chat --llm-model llamaguard-7b --llm-timeout-sec 30 --llm-max-concurrency 2 --llm-context-length 2000 --llm-max-input-chars 1200 --llm-temperature 0.0
```

### 4) Сохранение результатов в CSV

```powershell
python benchmark_moderation.py --count 300 --runs 3 --output-csv benchmark_results.csv
```

## Что попадает в итоговый CSV

Поля результата:

- method
- run_index
- elapsed_sec
- batch_size
- flagged
- throughput_msgs_sec
- tp
- fp
- tn
- fn
- accuracy
- precision
- recall
- f1
