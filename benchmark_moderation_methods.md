# benchmark_moderation.py: описание методов и возвращаемых значений

## Что сравнивает скрипт
Скрипт сравнивает 3 метода модерации:

- `classic` — классические правила/регексы (быстро, локально, без LLM).
- `llm` — проверка через LLM-клиент (`StubLLMClient` или `LMStudioGuardClient`).
- `hybrid` — комбинация classic + llm.

Результаты сравнения: скорость, пропускная способность и (если есть разметка) качество классификации.

## Основная модель результата

### `RunMetrics` (dataclass)
Назначение: хранит метрики одного измеренного прогона.

Поля:
- `method: str` — название метода (`classic`/`llm`/`hybrid`).
- `run_index: int` — номер прогона.
- `elapsed_sec: float` — время прогона в секундах.
- `batch_size: int` — размер батча.
- `flagged: int` — сколько текстов помечено как нарушение.
- `tp, fp, tn, fn: int | None` — элементы confusion matrix.
- `accuracy, precision, recall, f1: float | None` — метрики качества.

Возвращаемое значение: это структура данных (не функция), используется как элемент списка результатов.

## Методы LLM-стаба

### `StubLLMClient.__init__(latency_ms: float = 0.0) -> None`
Зачем нужен: создает локальный mock-клиент без внешней сети, чтобы тестировать `llm`/`hybrid` в изоляции.

Что возвращает: `None`.

### `StubLLMClient.moderate_text(text: str) -> dict`
Зачем нужен: имитирует модерацию текста через простые ключевые слова и regex.

Что возвращает:
- словарь формата модерации:
  - `violation: bool` — есть ли нарушение;
  - `score: int` — `1` если нарушение, иначе `0`;
  - `matched_rules: list[str]` — сработавшие правила;
  - `details: dict` — служебные данные (`provider: stub`).

### `StubLLMClient.close() -> None`
Зачем нужен: совместимость интерфейса с реальным клиентом.

Что возвращает: `None`.

## Методы реального клиента LM Studio

### `LMStudioGuardClient.__init__(...) -> None`
Зачем нужен: инициализирует HTTP-клиент, лимиты конкуренции и параметры запроса к LLM endpoint.

Что возвращает: `None`.

### `LMStudioGuardClient._extract_label(payload: dict) -> str | None`
Зачем нужен: извлекает метку `safe`/`unsafe` из разных форматов ответа API.

Что возвращает:
- `"safe"` или `"unsafe"`, если метка найдена;
- `None`, если распарсить не удалось.

### `LMStudioGuardClient.moderate_text(text: str) -> dict`
Зачем нужен: отправляет текст в LM Studio и нормализует ответ в единый формат модерации.

Что возвращает:
- словарь модерации:
  - `violation: bool`;
  - `score: int`;
  - `matched_rules: list[str]`;
  - `details: dict` с причиной ошибок (`timeout`, `http_*`, `context_overflow`, `parse_error`) или с меткой.

Примечание: при ошибках сети/парсинга метод не падает исключением, а возвращает «без нарушения» с диагностикой в `details`.

### `LMStudioGuardClient.close() -> None`
Зачем нужен: корректно закрывает `httpx.AsyncClient`.

Что возвращает: `None`.

## Функции бенчмарка

### `benchmark_method(...) -> list[RunMetrics]`
Зачем нужен: выполняет warmup и измеренные прогоны для одного метода (`classic`/`llm`/`hybrid`).

Что возвращает:
- список `RunMetrics` по всем измеренным прогонам.

### `compute_quality_metrics(y_true, y_pred) -> tuple[int, int, int, int, float, float, float, float]`
Зачем нужен: считает confusion matrix и метрики качества классификации.

Что возвращает кортеж:
- `(tp, fp, tn, fn, accuracy, precision, recall, f1)`.

### `print_summary(all_runs: list[RunMetrics]) -> None`
Зачем нужен: печатает агрегированные итоги по скорости и качеству в консоль.

Что возвращает: `None`.

### `maybe_write_csv(output_csv: str | None, all_runs: list[RunMetrics]) -> None`
Зачем нужен: при заданном пути сохраняет детальные результаты прогонов в CSV.

Что возвращает: `None`.

### `build_text_batch(text: str, count: int) -> list[str]`
Зачем нужен: формирует батч одинаковых сообщений (режим без CSV).

Что возвращает:
- список строк длины `count`.

### `load_texts_from_csv(...) -> tuple[list[str], list[int] | None]`
Зачем нужен: читает тексты из CSV, выбирает `count` строк (`first`/`random`) и опционально формирует бинарные метки.

Что возвращает:
- `texts: list[str]`;
- `labels: list[int] | None` (если `label_column` не задан, вернет `None`).

### `resolve_texts(args: argparse.Namespace) -> tuple[list[str], list[int] | None]`
Зачем нужен: выбирает источник текста (CSV или одиночная строка).

Что возвращает:
- `(texts, labels)` в едином формате для бенчмарка.

### `run_benchmark(args: argparse.Namespace) -> None`
Зачем нужен: оркестрирует весь процесс — создание клиентов, запуск методов, сбор метрик, вывод summary и запись CSV.

Что возвращает: `None`.

### `parse_args() -> argparse.Namespace`
Зачем нужен: объявляет и парсит CLI-параметры запуска.

Что возвращает:
- объект `argparse.Namespace` со всеми параметрами.

### `main() -> None`
Зачем нужен: точка входа. Валидирует базовые аргументы и запускает async-бенчмарк.

Что возвращает: `None`.

## Коротко по формату модерации (`dict`)
Единый формат, который ожидается от LLM-клиента:

- `violation: bool` — нарушает ли текст политику.
- `score: int` — бинарный скор (`1`/`0`).
- `matched_rules: list[str]` — список сработавших правил/лейблов.
- `details: dict` — диагностическая информация о провайдере и ошибках.

Именно из `violation` в дальнейшем строятся предсказания для quality-метрик.
