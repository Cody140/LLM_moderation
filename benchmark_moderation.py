from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from time import perf_counter

import httpx

from app.moderators.classic import ClassicModerator
from app.moderators.hybrid import HybridModerator
from app.moderators.llm import LLMModerator

CSV_LABEL_COLUMNS = [
    "toxicity",
    "severe_toxicity",
    "obscene",
    "threat",
    "insult",
    "identity_attack",
    "sexual_explicit",
]
REQUIRED_CSV_COLUMNS = ["text", *CSV_LABEL_COLUMNS]


@dataclass
class DatasetSample:
    row_id: int
    text: str
    expected_label: bool
    primary_case_type: str
    active_labels: list[str]
    multi_label_flag: bool


@dataclass
class SampleBenchmarkResult:
    run_index: int
    row_id: int
    method: str
    text: str
    expected_label: bool
    predicted_label: bool | None
    status: str
    error_type: str | None
    latency_sec: float
    score: float | None
    matched_rules: list[str]
    decision_type: str | None
    decision_reason: str | None
    route: str | None
    primary_case_type: str
    active_labels: list[str]
    multi_label_flag: bool
    raw_model_label: str | None
    raw_response: str | None
    predicted_category: str | None = None
    category_match: bool | None = None


@dataclass
class SummaryMetrics:
    method: str
    total_samples: int
    processed_ok: int
    processing_errors: int
    error_rate: float
    harmful_total: int
    harmful_detected: int
    harmful_missed: int
    clean_total: int
    clean_flagged: int
    clean_correct: int
    tp: int
    fp: int
    tn: int
    fn: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    fpr: float
    fnr: float
    elapsed_sec: float
    throughput_msgs_sec: float
    avg_latency_sec: float
    mean_latency_sec: float
    median_latency_sec: float
    min_latency_sec: float
    max_latency_sec: float
    quality_metrics: dict[str, float]
    reliability_metrics: dict[str, int | float | dict[str, int]]
    error_count_by_type: dict[str, int]


@dataclass
class CaseTypeMetricRow:
    method: str
    case_type: str
    count: int
    processed_ok: int
    accuracy: float
    precision: float
    recall: float
    f1: float


class StubLLMClient:
    """Local async stub used for deterministic benchmark runs without external API calls."""

    def __init__(self, latency_ms: float = 0.0) -> None:
        self._latency_sec = max(latency_ms, 0.0) / 1000.0
        self._toxic_words = {"idiot", "moron", "stupid", "kill", "hate", "loser", "trash"}
        self._toxic_patterns = [
            ("masked_stupid", re.compile(r"(?<![a-z0-9])[-_*]upid\b", re.IGNORECASE)),
        ]

    async def moderate_text(self, text: str) -> dict:
        if self._latency_sec > 0:
            await asyncio.sleep(self._latency_sec)

        lowered = text.lower()
        keyword_hit = any(word in lowered for word in self._toxic_words)
        regex_hits = [name for name, pattern in self._toxic_patterns if pattern.search(text)]
        violation = keyword_hit or bool(regex_hits)

        matched_rules: list[str] = []
        if keyword_hit:
            matched_rules.append("stub:keyword")
        matched_rules.extend(f"stub:regex:{name}" for name in regex_hits)

        label = "unsafe" if violation else "safe"
        return {
            "status": "ok",
            "violation": violation,
            "score": 1.0 if violation else 0.0,
            "matched_rules": matched_rules,
            "raw_label": label,
            "details": {"provider": "stub"},
        }

    async def close(self) -> None:
        return None


class LMStudioGuardClient:
    """Client for LM Studio style endpoint.

    Supports multiple prompt formats via prompt_version:
      - 'llamaguard_o6'  : LlamaGuard 7B (O1-O6, safe/unsafe)
      - 'llamaguard_s13' : Llama Guard 3 1B/8B (S1-S13, safe/unsafe)
      - 'shieldgemma'    : ShieldGemma 2B/9B (Yes/No)
      - 'qwen_civil'     : Qwen2.5 Instruct with custom prompt + JSON output
                           (label + category from Civil Comments taxonomy)
    """

    PROMPT_VERSIONS = (
        "llamaguard_o6",
        "llamaguard_s13",
        "shieldgemma",
        "qwen_civil",
        "qwen_civil_v2",
        "qwen_civil_v3",
    )

    _MAX_TOKENS_BY_VERSION = {
        "llamaguard_o6": 32,
        "llamaguard_s13": 64,
        "shieldgemma": 16,
        "qwen_civil": 64,
        "qwen_civil_v2": 80,
        "qwen_civil_v3": 64,
    }

    _LLAMAGUARD_O6_TEMPLATE = (
        "Task: Check if there is unsafe content in 'User' messages in conversations "
        "according to the safety policy with the below categories.\n\n"
        "<BEGIN UNSAFE CONTENT CATEGORIES>\n"
        "O1: Violence and Hate.\nO2: Sexual Content.\nO3: Criminal Planning.\n"
        "O4: Guns and Illegal Weapons.\nO5: Regulated or Controlled Substances.\n"
        "O6: Self-Harm.\n<END UNSAFE CONTENT CATEGORIES>\n\n"
        "<BEGIN CONVERSATION>\n"
        "User: {text}\n"
        "<END CONVERSATION>\n\n"
        "Provide your safety assessment for ONLY THE LAST User message in the above conversation:\n"
        "- First line must read 'safe' or 'unsafe'.\n"
        "- If unsafe, a second line must include a comma-separated list of violated categories."
    )

    _LLAMAGUARD_S13_TEMPLATE = (
        "Task: Check if there is unsafe content in 'User' messages in conversations "
        "according our safety policy with the below categories.\n\n"
        "<BEGIN UNSAFE CONTENT CATEGORIES>\n"
        "S1: Violent Crimes.\nS2: Non-Violent Crimes.\nS3: Sex Crimes.\n"
        "S4: Child Exploitation.\nS5: Defamation.\nS6: Specialized Advice.\n"
        "S7: Privacy.\nS8: Intellectual Property.\nS9: Indiscriminate Weapons.\n"
        "S10: Hate.\nS11: Self-Harm.\nS12: Sexual Content.\nS13: Elections.\n"
        "<END UNSAFE CONTENT CATEGORIES>\n\n"
        "<BEGIN CONVERSATION>\n"
        "User: {text}\n"
        "<END CONVERSATION>\n\n"
        "Provide your safety assessment for ONLY THE LAST User message in the above conversation:\n"
        "- First line must read 'safe' or 'unsafe'.\n"
        "- If unsafe, a second line must include a comma-separated list of violated categories."
    )

    _SHIELDGEMMA_TEMPLATE = (
        "You are a policy expert trying to help determine whether a user message is in "
        "violation of the defined safety policies.\n\n"
        "<start_of_turn>\nHuman Question: {text}\n<end_of_turn>\n\n"
        "Our safety principle is defined below:\n"
        "* \"No Harassment\": The message shall not contain malicious, intimidating, "
        "bullying, or abusive content targeting another individual (e.g., physical "
        "threats, denial of tragic events, disparaging victims of violence).\n"
        "* \"No Hate Speech\": The message shall not target identity and/or protected "
        "attributes (e.g., racial slurs, promotion of discrimination, calls to violence "
        "against protected groups).\n"
        "* \"No Sexually Explicit Information\": The message shall not contain references "
        "to sexual acts or other lewd content.\n"
        "* \"No Dangerous Content\": The message shall not promote or enable access to "
        "harmful goods, services, and activities.\n\n"
        "Does the human message violate the above principle? Your answer must start "
        "with 'Yes' or 'No'. And then walk through step by step to be sure we answer "
        "correctly."
    )

    _QWEN_CIVIL_TEMPLATE = (
        "Comment:\n{text}\n\n"
        "Classify the comment using EXACTLY this JSON format:\n"
        "{{\"label\": \"harmful\" or \"safe\", \"category\": one of "
        "[\"insult\", \"threat\", \"obscene\", \"identity_attack\", \"sexual_explicit\", "
        "\"severe_toxicity\", \"none\"]}}\n\n"
        "Use category \"none\" only when label is \"safe\". "
        "Pick the SINGLE most fitting category for harmful comments. "
        "Return ONLY the JSON object, no explanation."
    )

    _QWEN_DEFAULT_SYSTEM = (
        "You are a strict English-language content moderator for an online discussion "
        "platform. You classify comments using the Civil Comments taxonomy. A comment "
        "is \"harmful\" if it contains insults targeting a person/group, threats, "
        "identity-based attacks, sexual content, severe obscenity, or general toxicity. "
        "Reply ONLY with the JSON object specified in the user message. Do not explain."
    )

    _QWEN_V2_SYSTEM = (
        "You are an expert content moderator for an English-language online news "
        "comments platform (Civil Comments / Jigsaw dataset). Your task is to classify "
        "each comment using a strict taxonomy of harm categories.\n\n"
        "Output rules:\n"
        "- Reply with ONLY a JSON object matching the schema.\n"
        "- No reasoning, no preface, no markdown fences. Just JSON.\n"
        "- If a comment is opinionated, sarcastic, or critical but contains no "
        "profanity targeting a person/group, label it \"safe\".\n"
        "- For harmful comments, pick the SINGLE most specific category using priority: "
        "threat > sexual_explicit > identity_attack > obscene > severe_toxicity > insult."
    )

    _QWEN_CIVIL_V2_TEMPLATE = (
        "Comment:\n{text}\n\n"
        "Definitions (STRICT interpretation):\n\n"
        "- threat            : explicit statement, wish, or call for physical violence "
        "against a person or group (\"kill them\", \"should be shot\", \"die\").\n"
        "- sexual_explicit   : detailed sexual descriptions, body parts in sexual "
        "context, or lewd content. NOT casual profanity.\n"
        "- identity_attack   : derogatory content TARGETING a PROTECTED ATTRIBUTE "
        "(race, religion, ethnicity, nationality, gender, sexual orientation, "
        "disability). Must explicitly attack the group, not just mention it.\n"
        "- obscene           : strong profanity (fuck, shit, bullshit) used in the "
        "comment WITHOUT targeting a specific person or protected group.\n"
        "- severe_toxicity   : extremely hostile, dehumanizing, or hateful tone "
        "overall. Use only when content is clearly aggressive but none of the more "
        "specific categories fit.\n"
        "- insult            : derogatory remark aimed at a person or group based on "
        "behavior, intelligence, or general worth (NOT protected attributes - that "
        "would be identity_attack).\n"
        "- none              : safe. Includes strong opinions, political criticism, "
        "sarcasm, even mild rudeness without profanity.\n\n"
        "Priority: if multiple apply, pick the one HIGHEST in this list: "
        "threat > sexual_explicit > identity_attack > obscene > severe_toxicity > insult.\n\n"
        "Output the JSON object ONLY (no other text):\n"
        "{{\"label\": \"harmful\" or \"safe\", \"category\": one of "
        "[threat, sexual_explicit, identity_attack, obscene, severe_toxicity, insult, none]}}"
    )

    _QWEN_V3_SYSTEM = (
        "You are a content moderator for the Civil Comments dataset. Output strict "
        "JSON per the schema. No commentary, no markdown fences, no reasoning."
    )

    _QWEN_CIVIL_V3_TEMPLATE = (
        "Comment:\n{text}\n\n"
        "Classify the comment. Pick ONE label and ONE category.\n\n"
        "Categories (priority order: if multiple apply, pick the FIRST):\n\n"
        "1. threat            : explicit physical violence. "
        "Examples: \"kill them\", \"should be shot\", \"hope you die\".\n"
        "2. sexual_explicit   : detailed sexual content, body parts in sexual context, "
        "or lewd descriptions.\n"
        "3. identity_attack   : attacks on race, religion, ethnicity, nationality, "
        "gender, sexual orientation, or disability. "
        "Examples: \"those <slur> always\", \"go back to your country\".\n"
        "4. obscene           : strong profanity NOT directed at a specific person or "
        "protected group. Examples: \"this is fucking bullshit\", \"what a shitshow\", "
        "\"holy crap\".\n"
        "5. severe_toxicity   : extremely hostile, dehumanizing, or wishing-harm "
        "language overall, when no more specific category fits. "
        "Examples: \"those people are vermin\", \"scum of the earth\".\n"
        "6. insult            : derogatory remarks about a person's behavior, "
        "intelligence, or worth (NOT a protected attribute). "
        "Examples: \"you're an idiot\", \"useless moron\", \"loser\".\n"
        "7. none              : safe.\n\n"
        "Important:\n"
        "- A comment is \"harmful\" only if it contains EXPLICIT profanity, threats, "
        "identity-based attacks, sexual content, or direct insults toward a person.\n"
        "- Strong opinions, sarcasm, political criticism, and disagreement are NOT "
        "harmful by themselves.\n\n"
        "Return JSON only: "
        "{{\"label\": \"harmful\" or \"safe\", \"category\": \"...\"}}"
    )

    _QWEN_CATEGORIES = {
        "insult", "threat", "obscene", "identity_attack",
        "sexual_explicit", "severe_toxicity", "none",
    }

    def __init__(
        self,
        base_url: str,
        endpoint_path: str,
        model: str,
        timeout_seconds: float,
        max_concurrency: int,
        auth_token: str | None,
        temperature: float,
        context_length: int,
        max_input_chars: int,
        prompt_version: str = "llamaguard_o6",
        system_prompt: str = "",
    ) -> None:
        if prompt_version not in self.PROMPT_VERSIONS:
            raise ValueError(
                f"Unknown prompt_version '{prompt_version}'. "
                f"Allowed: {', '.join(self.PROMPT_VERSIONS)}"
            )
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)
        self._endpoint_path = endpoint_path
        self._model = model
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._auth_token = auth_token
        self._temperature = temperature
        self._context_length = context_length
        self._max_input_chars = max_input_chars
        self._prompt_version = prompt_version
        if not system_prompt:
            if prompt_version == "qwen_civil":
                system_prompt = self._QWEN_DEFAULT_SYSTEM
            elif prompt_version == "qwen_civil_v2":
                system_prompt = self._QWEN_V2_SYSTEM
            elif prompt_version == "qwen_civil_v3":
                system_prompt = self._QWEN_V3_SYSTEM
        self._system_prompt = system_prompt

    def _build_prompt(self, text: str) -> str:
        templates = {
            "llamaguard_o6": self._LLAMAGUARD_O6_TEMPLATE,
            "llamaguard_s13": self._LLAMAGUARD_S13_TEMPLATE,
            "shieldgemma": self._SHIELDGEMMA_TEMPLATE,
            "qwen_civil": self._QWEN_CIVIL_TEMPLATE,
            "qwen_civil_v2": self._QWEN_CIVIL_V2_TEMPLATE,
            "qwen_civil_v3": self._QWEN_CIVIL_V3_TEMPLATE,
        }
        return templates[self._prompt_version].format(text=text)

    def _get_content(self, payload: dict) -> str | None:
        output = payload.get("output")
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, dict):
                content = first.get("content")
                if isinstance(content, str):
                    return content
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
        return None

    def _extract_label(self, payload: dict) -> tuple[str | None, str | None]:
        """Return (label, predicted_category).

        label is normalized to 'safe' / 'unsafe' / None (parse error).
        predicted_category may be None.
        """
        content = self._get_content(payload)
        if not isinstance(content, str) or not content.strip():
            return None, None
        version = self._prompt_version

        if version in ("qwen_civil", "qwen_civil_v2", "qwen_civil_v3"):
            return self._parse_qwen_json(content)

        first_line = content.strip().lower().splitlines()[0].strip()

        if version == "shieldgemma":
            if first_line.startswith("yes"):
                return "unsafe", None
            if first_line.startswith("no"):
                return "safe", None
            return None, None

        # llamaguard_o6 / llamaguard_s13: 'safe' / 'unsafe\n<categories>'
        if first_line in {"safe", "unsafe"}:
            category = None
            if first_line == "unsafe":
                lines = content.strip().lower().splitlines()
                if len(lines) > 1:
                    category = lines[1].strip() or None
            return first_line, category
        return None, None

    def _parse_qwen_json(self, content: str) -> tuple[str | None, str | None]:
        import json as _json
        text = content.strip()
        # Some models wrap JSON in markdown fences; strip them.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
        # Find first '{' and last '}' to handle leading/trailing text.
        l = text.find("{")
        r = text.rfind("}")
        if l < 0 or r < 0 or r <= l:
            return None, None
        try:
            parsed = _json.loads(text[l : r + 1])
        except Exception:
            return None, None
        if not isinstance(parsed, dict):
            return None, None
        lbl_raw = parsed.get("label")
        cat_raw = parsed.get("category")
        label: str | None = None
        if isinstance(lbl_raw, str):
            lower = lbl_raw.strip().lower()
            if lower == "harmful":
                label = "unsafe"
            elif lower == "safe":
                label = "safe"
        category: str | None = None
        if isinstance(cat_raw, str):
            cat_lower = cat_raw.strip().lower()
            if cat_lower in self._QWEN_CATEGORIES:
                category = cat_lower
        return label, category

    async def moderate_text(self, text: str) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        truncated = text[: self._max_input_chars]
        prompt = self._build_prompt(truncated)
        max_tokens = self._MAX_TOKENS_BY_VERSION[self._prompt_version]
        messages: list[dict] = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": max_tokens,
        }

        payload: dict | None = None
        for attempt in range(3):
            async with self._semaphore:
                try:
                    response = await self._client.post(self._endpoint_path, headers=headers, json=body)
                    response.raise_for_status()
                    payload = response.json()
                except httpx.TimeoutException:
                    return {
                        "status": "error",
                        "error_type": "timeout",
                        "matched_rules": [],
                        "details": {"provider": "lmstudio"},
                    }
                except httpx.HTTPStatusError as exc:
                    if attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    return {
                        "status": "error",
                        "error_type": "http_error",
                        "matched_rules": [],
                        "details": {
                            "provider": "lmstudio",
                            "status_code": exc.response.status_code,
                        },
                    }
                except Exception:
                    return {
                        "status": "error",
                        "error_type": "unknown_error",
                        "matched_rules": [],
                        "details": {"provider": "lmstudio"},
                    }

            if not isinstance(payload, dict):
                return {
                    "status": "error",
                    "error_type": "invalid_response",
                    "matched_rules": [],
                    "details": {"provider": "lmstudio"},
                }

            parsed = self._extract_label(payload)
            label, predicted_category = parsed
            if label is not None:
                break
        else:
            return {
                "status": "error",
                "error_type": "parse_error",
                "matched_rules": [],
                "details": {"provider": "lmstudio", "parse_error": "label_not_found"},
            }

        violation = label == "unsafe"
        matched_rules = [f"llm:{label}"]
        if predicted_category:
            matched_rules.append(f"llm:cat:{predicted_category}")
        return {
            "status": "ok",
            "violation": violation,
            "score": 1.0 if violation else 0.0,
            "matched_rules": matched_rules,
            "raw_label": label,
            "details": {
                "provider": "lmstudio",
                "label": label,
                "predicted_category": predicted_category,
                "prompt_version": self._prompt_version,
                "raw_payload": payload,
            },
        }

    async def close(self) -> None:
        await self._client.aclose()


def _parse_float(value: str | None, column_name: str, row_index: int) -> float:
    if value is None:
        raise ValueError(f"Row {row_index}: missing value for '{column_name}'")
    raw = value.strip()
    if raw == "":
        raise ValueError(f"Row {row_index}: empty value for '{column_name}'")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Row {row_index}: invalid float for '{column_name}': '{raw}'") from exc


def build_binary_label(row: dict[str, str], row_index: int) -> bool:
    """Build binary harmful label from dataset dimensions.

    A sample is harmful when at least one moderation dimension is > 0.
    """

    return any(_parse_float(row.get(column), column, row_index) > 0.0 for column in CSV_LABEL_COLUMNS)


def derive_case_types(row: dict[str, str], row_index: int) -> tuple[str, list[str], bool]:
    active = [column for column in CSV_LABEL_COLUMNS if _parse_float(row.get(column), column, row_index) > 0.0]
    if not active:
        return "clean", [], False

    if _parse_float(row.get("threat"), "threat", row_index) > 0.0:
        primary = "threat"
    elif _parse_float(row.get("sexual_explicit"), "sexual_explicit", row_index) > 0.0:
        primary = "sexual_explicit"
    elif _parse_float(row.get("identity_attack"), "identity_attack", row_index) > 0.0:
        primary = "identity_attack"
    elif _parse_float(row.get("obscene"), "obscene", row_index) > 0.0:
        primary = "obscene"
    elif _parse_float(row.get("severe_toxicity"), "severe_toxicity", row_index) > 0.0:
        primary = "severe_toxicity"
    elif _parse_float(row.get("insult"), "insult", row_index) > 0.0:
        primary = "insult"
    else:
        primary = "harmful"

    return primary, active, len(active) > 1


def load_dataset_from_csv(csv_path: str) -> list[DatasetSample]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    samples: list[DatasetSample] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError(f"CSV has no header row: {path}")

            missing_columns = [column for column in REQUIRED_CSV_COLUMNS if column not in reader.fieldnames]
            if missing_columns:
                available = ", ".join(reader.fieldnames)
                raise ValueError(
                    "CSV is missing required columns: "
                    f"{', '.join(missing_columns)}. Available columns: {available}"
                )

            for row_number, row in enumerate(reader, start=2):
                raw_text = row.get("text")
                if raw_text is None:
                    continue

                text = raw_text.strip()
                if not text:
                    continue

                expected_label = build_binary_label(row, row_number)
                primary_case_type, active_labels, multi_label_flag = derive_case_types(row, row_number)
                samples.append(
                    DatasetSample(
                        row_id=row_number,
                        text=text,
                        expected_label=expected_label,
                        primary_case_type=primary_case_type,
                        active_labels=active_labels,
                        multi_label_flag=multi_label_flag,
                    )
                )
                
    except UnicodeDecodeError as exc:
        raise ValueError(f"CSV decoding error for {path}: {exc}") from exc
    except csv.Error as exc:
        raise ValueError(f"CSV parsing error for {path}: {exc}") from exc

    if not samples:
        raise ValueError(f"No valid non-empty rows found in CSV: {path}")

    return samples


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_quality_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float | int]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal length")

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    accuracy = _safe_div(tp + tn, len(y_true))
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "fnr": fnr,
    }


def summarize_method(method: str, per_sample: list[SampleBenchmarkResult], elapsed_sec: float) -> SummaryMetrics:
    total_samples = len(per_sample)
    ok_samples = [item for item in per_sample if item.status == "ok" and item.predicted_label is not None]
    error_samples = [item for item in per_sample if item.status != "ok"]
    harmful_total = sum(1 for item in per_sample if item.expected_label)
    clean_total = total_samples - harmful_total

    y_true = [1 if item.expected_label else 0 for item in ok_samples]
    y_pred = [1 if bool(item.predicted_label) else 0 for item in ok_samples]
    quality = compute_quality_metrics(y_true, y_pred) if ok_samples else {
        "tp": 0,
        "fp": 0,
        "tn": 0,
        "fn": 0,
        "accuracy": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "fpr": 0.0,
        "fnr": 0.0,
    }

    latencies = [item.latency_sec for item in per_sample if item.latency_sec >= 0.0]
    mean_latency = mean(latencies) if latencies else 0.0
    median_latency = median(latencies) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    error_counts = Counter(item.error_type for item in error_samples if item.error_type)

    return SummaryMetrics(
        method=method,
        total_samples=total_samples,
        processed_ok=len(ok_samples),
        processing_errors=len(error_samples),
        error_rate=_safe_div(len(error_samples), total_samples),
        harmful_total=harmful_total,
        harmful_detected=int(quality["tp"]),
        harmful_missed=int(quality["fn"]),
        clean_total=clean_total,
        clean_flagged=int(quality["fp"]),
        clean_correct=int(quality["tn"]),
        tp=int(quality["tp"]),
        fp=int(quality["fp"]),
        tn=int(quality["tn"]),
        fn=int(quality["fn"]),
        accuracy=float(quality["accuracy"]),
        precision=float(quality["precision"]),
        recall=float(quality["recall"]),
        f1=float(quality["f1"]),
        fpr=float(quality["fpr"]),
        fnr=float(quality["fnr"]),
        elapsed_sec=elapsed_sec,
        throughput_msgs_sec=_safe_div(total_samples, elapsed_sec),
        avg_latency_sec=_safe_div(elapsed_sec, total_samples),
        mean_latency_sec=mean_latency,
        median_latency_sec=median_latency,
        min_latency_sec=min_latency,
        max_latency_sec=max_latency,
        quality_metrics={
            "accuracy": float(quality["accuracy"]),
            "precision": float(quality["precision"]),
            "recall": float(quality["recall"]),
            "f1": float(quality["f1"]),
            "fpr": float(quality["fpr"]),
            "fnr": float(quality["fnr"]),
        },
        reliability_metrics={
            "processed_ok": len(ok_samples),
            "processing_errors": len(error_samples),
            "error_rate": _safe_div(len(error_samples), total_samples),
            "error_count_by_type": dict(error_counts),
        },
        error_count_by_type=dict(error_counts),
    )


async def _run_single_sample(
    sample: DatasetSample,
    method_name: str,
    moderator,
    run_index: int,
) -> SampleBenchmarkResult:
    sample_t0 = perf_counter()
    response = await moderator.moderate_batch([sample.text])
    sample_latency = perf_counter() - sample_t0

    prediction = response.results[0] if response.results else None
    if prediction is None:
        return SampleBenchmarkResult(
            run_index=run_index,
            row_id=sample.row_id,
            method=method_name,
            text=sample.text,
            expected_label=sample.expected_label,
            predicted_label=None,
            status="error",
            error_type="invalid_response",
            latency_sec=sample_latency,
            score=None,
            matched_rules=[],
            decision_type="uncertain",
            decision_reason="missing_prediction",
            route="llm_fallback" if method_name in {"llm", "hybrid"} else "classic_only",
            primary_case_type=sample.primary_case_type,
            active_labels=sample.active_labels,
            multi_label_flag=sample.multi_label_flag,
            raw_model_label=None,
            raw_response=None,
        )

    status = getattr(prediction, "status", "ok") or "ok"
    error_type = getattr(prediction, "error_type", None)
    predicted_label = prediction.violation if status == "ok" else None
    details = prediction.details if isinstance(prediction.details, dict) else {}
    raw_response = details.get("raw_payload")
    if raw_response is not None:
        raw_response = json.dumps(raw_response, ensure_ascii=False)

    predicted_category = details.get("predicted_category") if isinstance(details, dict) else None
    category_match: bool | None = None
    if predicted_category and predicted_category != "none":
        category_match = predicted_category == sample.primary_case_type

    return SampleBenchmarkResult(
        run_index=run_index,
        row_id=sample.row_id,
        method=method_name,
        text=sample.text,
        expected_label=sample.expected_label,
        predicted_label=predicted_label,
        status=status,
        error_type=error_type,
        latency_sec=sample_latency,
        score=prediction.score,
        matched_rules=prediction.matched_rules,
        decision_type=getattr(prediction, "decision_type", None),
        decision_reason=getattr(prediction, "decision_reason", None) or details.get("decision_reason"),
        route=getattr(prediction, "route", None) or details.get("route"),
        primary_case_type=sample.primary_case_type,
        active_labels=sample.active_labels,
        multi_label_flag=sample.multi_label_flag,
        raw_model_label=details.get("label") or details.get("raw_label"),
        raw_response=raw_response,
        predicted_category=predicted_category,
        category_match=category_match,
    )


async def benchmark_method(
    method_name: str,
    moderator,
    samples: list[DatasetSample],
    warmup_runs: int,
    measured_runs: int,
) -> tuple[list[SampleBenchmarkResult], list[SummaryMetrics]]:
    for _ in range(warmup_runs):
        await asyncio.gather(*[moderator.moderate_batch([s.text]) for s in samples])

    all_sample_results: list[SampleBenchmarkResult] = []
    run_summaries: list[SummaryMetrics] = []

    for run_index in range(1, measured_runs + 1):
        t0 = perf_counter()
        run_results: list[SampleBenchmarkResult] = list(
            await asyncio.gather(
                *[_run_single_sample(sample, method_name, moderator, run_index) for sample in samples]
            )
        )
        elapsed = perf_counter() - t0

        run_summary = summarize_method(method_name, run_results, elapsed)
        run_summaries.append(run_summary)
        all_sample_results.extend(run_results)

        print(
            f"  run={run_index:>2} elapsed={elapsed:.4f}s total={run_summary.total_samples} "
            f"ok={run_summary.processed_ok} errors={run_summary.processing_errors} "
            f"err_rate={run_summary.error_rate:.4f} throughput={run_summary.throughput_msgs_sec:.2f} msg/s "
            f"avg_latency={run_summary.avg_latency_sec:.6f}s "
            f"acc={run_summary.accuracy:.4f} prec={run_summary.precision:.4f} rec={run_summary.recall:.4f} "
            f"f1={run_summary.f1:.4f} fpr={run_summary.fpr:.4f} fnr={run_summary.fnr:.4f}"
        )

    return all_sample_results, run_summaries


def aggregate_method_summaries(method: str, method_rows: list[SampleBenchmarkResult]) -> SummaryMetrics:
    if not method_rows:
        return summarize_method(method, [], 0.0)

    elapsed_sec = sum(
        row.latency_sec
        for row in method_rows
    )
    return summarize_method(method, method_rows, elapsed_sec)


def compute_case_type_metrics(method: str, method_rows: list[SampleBenchmarkResult]) -> list[CaseTypeMetricRow]:
    case_types = ["insult", "threat", "obscene", "identity_attack", "sexual_explicit", "clean"]
    rows: list[CaseTypeMetricRow] = []

    for case_type in case_types:
        subset = [item for item in method_rows if item.primary_case_type == case_type]
        ok_subset = [item for item in subset if item.status == "ok" and item.predicted_label is not None]
        y_true = [1 if item.expected_label else 0 for item in ok_subset]
        y_pred = [1 if bool(item.predicted_label) else 0 for item in ok_subset]
        quality = compute_quality_metrics(y_true, y_pred) if ok_subset else {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }
        rows.append(
            CaseTypeMetricRow(
                method=method,
                case_type=case_type,
                count=len(subset),
                processed_ok=len(ok_subset),
                accuracy=float(quality["accuracy"]),
                precision=float(quality["precision"]),
                recall=float(quality["recall"]),
                f1=float(quality["f1"]),
            )
        )

    return rows


def compute_category_confusion(method_rows: list[SampleBenchmarkResult]) -> dict:
    """Multi-class category prediction stats (only for samples where the model
    returned a non-empty predicted_category — i.e. exp08 with qwen_civil).

    Returns dict with:
      - total_with_prediction
      - exact_match (predicted == primary_case_type)
      - per_category accuracy
      - confusion: list[{true, pred, count}]
    """
    rows_with_cat = [r for r in method_rows if r.predicted_category]
    if not rows_with_cat:
        return {}
    exact = sum(1 for r in rows_with_cat if r.category_match)
    confusion: dict[tuple[str, str], int] = {}
    per_cat_total: Counter = Counter()
    per_cat_correct: Counter = Counter()
    for r in rows_with_cat:
        key = (r.primary_case_type, r.predicted_category or "none")
        confusion[key] = confusion.get(key, 0) + 1
        per_cat_total[r.primary_case_type] += 1
        if r.category_match:
            per_cat_correct[r.primary_case_type] += 1
    per_cat_accuracy = {
        cat: per_cat_correct[cat] / per_cat_total[cat]
        for cat in per_cat_total
        if per_cat_total[cat] > 0
    }
    return {
        "total_with_prediction": len(rows_with_cat),
        "exact_match": exact,
        "exact_match_rate": exact / len(rows_with_cat) if rows_with_cat else 0.0,
        "per_category_accuracy": per_cat_accuracy,
        "confusion": [{"true": t, "pred": p, "count": c} for (t, p), c in confusion.items()],
    }


def print_summary(summaries: list[SummaryMetrics]) -> None:
    print("\n=== Moderation Benchmark Summary ===")
    print(
        "method   | total | ok | err | err_rate | tp | fp | tn | fn | acc | prec | rec | f1 | fpr | fnr | elapsed | throughput | avg_lat"
    )
    print("-" * 166)
    for row in summaries:
        print(
            f"{row.method:<8} | {row.total_samples:>5} | {row.processed_ok:>3} | {row.processing_errors:>3} "
            f"| {row.error_rate:>8.4f} | {row.tp:>2} | {row.fp:>2} | {row.tn:>2} | {row.fn:>2} "
            f"| {row.accuracy:>4.3f} | {row.precision:>5.3f} | {row.recall:>4.3f} | {row.f1:>4.3f} "
            f"| {row.fpr:>5.3f} | {row.fnr:>5.3f} | {row.elapsed_sec:>7.3f}s "
            f"| {row.throughput_msgs_sec:>10.2f} | {row.avg_latency_sec:>7.5f}s"
        )
        if row.error_count_by_type:
            print(f"  error_count_by_type: {row.error_count_by_type}")
        print(
            "  harmful/clean: "
            f"harmful_total={row.harmful_total} harmful_detected={row.harmful_detected} harmful_missed={row.harmful_missed} "
            f"clean_total={row.clean_total} clean_flagged={row.clean_flagged} clean_correct={row.clean_correct}"
        )
        print(f"  quality_metrics: {row.quality_metrics}")
        print(f"  reliability_metrics: {row.reliability_metrics}")


def write_detailed_results(path: str, rows: list[SampleBenchmarkResult]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "run_index",
                "row_id",
                "method",
                "text",
                "expected_label",
                "predicted_label",
                "status",
                "error_type",
                "latency_sec",
                "score",
                "matched_rules",
                "decision_type",
                "decision_reason",
                "route",
                "primary_case_type",
                "active_labels",
                "multi_label_flag",
                "raw_model_label",
                "raw_response",
                "predicted_category",
                "category_match",
            ]
        )
        for item in rows:
            writer.writerow(
                [
                    item.run_index,
                    item.row_id,
                    item.method,
                    item.text,
                    int(item.expected_label),
                    "" if item.predicted_label is None else int(item.predicted_label),
                    item.status,
                    item.error_type or "",
                    f"{item.latency_sec:.8f}",
                    "" if item.score is None else f"{item.score:.6f}",
                    "|".join(item.matched_rules),
                    item.decision_type or "",
                    item.decision_reason or "",
                    item.route or "",
                    item.primary_case_type,
                    "|".join(item.active_labels),
                    str(item.multi_label_flag),
                    item.raw_model_label or "",
                    item.raw_response or "",
                    item.predicted_category or "",
                    "" if item.category_match is None else str(item.category_match),
                ]
            )


def write_summary_results(path: str, rows: list[SummaryMetrics]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "method",
                "total_samples",
                "processed_ok",
                "processing_errors",
                "error_rate",
                "harmful_total",
                "harmful_detected",
                "harmful_missed",
                "clean_total",
                "clean_flagged",
                "clean_correct",
                "tp",
                "fp",
                "tn",
                "fn",
                "accuracy",
                "precision",
                "recall",
                "f1",
                "fpr",
                "fnr",
                "elapsed_sec",
                "throughput_msgs_sec",
                "avg_latency_sec",
                "mean_latency_sec",
                "median_latency_sec",
                "min_latency_sec",
                "max_latency_sec",
                "quality_metrics",
                "reliability_metrics",
                "error_count_by_type",
            ]
        )
        for item in rows:
            writer.writerow(
                [
                    item.method,
                    item.total_samples,
                    item.processed_ok,
                    item.processing_errors,
                    f"{item.error_rate:.8f}",
                    item.harmful_total,
                    item.harmful_detected,
                    item.harmful_missed,
                    item.clean_total,
                    item.clean_flagged,
                    item.clean_correct,
                    item.tp,
                    item.fp,
                    item.tn,
                    item.fn,
                    f"{item.accuracy:.8f}",
                    f"{item.precision:.8f}",
                    f"{item.recall:.8f}",
                    f"{item.f1:.8f}",
                    f"{item.fpr:.8f}",
                    f"{item.fnr:.8f}",
                    f"{item.elapsed_sec:.8f}",
                    f"{item.throughput_msgs_sec:.8f}",
                    f"{item.avg_latency_sec:.8f}",
                    f"{item.mean_latency_sec:.8f}",
                    f"{item.median_latency_sec:.8f}",
                    f"{item.min_latency_sec:.8f}",
                    f"{item.max_latency_sec:.8f}",
                    json.dumps(item.quality_metrics, ensure_ascii=False),
                    json.dumps(item.reliability_metrics, ensure_ascii=False),
                    json.dumps(item.error_count_by_type, ensure_ascii=False),
                ]
            )


def write_case_type_results(path: str, rows: list[CaseTypeMetricRow]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["method", "case_type", "count", "processed_ok", "accuracy", "precision", "recall", "f1"])
        for item in rows:
            writer.writerow(
                [
                    item.method,
                    item.case_type,
                    item.count,
                    item.processed_ok,
                    f"{item.accuracy:.8f}",
                    f"{item.precision:.8f}",
                    f"{item.recall:.8f}",
                    f"{item.f1:.8f}",
                ]
            )


async def run_benchmark(args: argparse.Namespace) -> None:
    samples = load_dataset_from_csv(args.texts_csv)
    if args.limit and args.limit > 0:
        samples = samples[: args.limit]

    methods = [item.strip().lower() for item in args.methods.split(",") if item.strip()]

    if args.llm_backend == "real":
        llm_client = LMStudioGuardClient(
            base_url=args.llm_base_url,
            endpoint_path=args.llm_endpoint_path,
            model=args.llm_model,
            timeout_seconds=args.llm_timeout_sec,
            max_concurrency=args.llm_max_concurrency,
            auth_token=args.llm_auth_token,
            temperature=args.llm_temperature,
            context_length=args.llm_context_length,
            max_input_chars=args.llm_max_input_chars,
            prompt_version=args.llm_prompt_version,
            system_prompt=args.llm_system_prompt or "",
        )
    else:
        llm_client = StubLLMClient(latency_ms=args.stub_latency_ms)

    classic = ClassicModerator()
    llm = LLMModerator(llm_client)
    hybrid = HybridModerator(classic, llm)

    moderators = {
        "classic": classic,
        "llm": llm,
        "hybrid": hybrid,
    }

    invalid_methods = [m for m in methods if m not in moderators]
    if invalid_methods:
        raise ValueError(
            f"Unknown methods: {', '.join(invalid_methods)}. Allowed: classic, llm, hybrid"
        )

    print("=== Benchmark Config ===")
    print(f"methods: {methods}")
    print(f"texts_csv: {args.texts_csv}")
    print(f"rows_loaded: {len(samples)}")
    print(f"warmup_runs: {args.warmup_runs}")
    print(f"measured_runs: {args.runs}")
    print(f"llm_backend: {args.llm_backend}")

    all_detailed: list[SampleBenchmarkResult] = []
    all_summary: list[SummaryMetrics] = []
    all_case_type_metrics: list[CaseTypeMetricRow] = []

    try:
        for method in methods:
            print(f"\nRunning method: {method}")
            detailed_rows, run_summaries = await benchmark_method(
                method_name=method,
                moderator=moderators[method],
                samples=samples,
                warmup_runs=args.warmup_runs,
                measured_runs=args.runs,
            )
            method_summary = aggregate_method_summaries(method, detailed_rows)
            all_detailed.extend(detailed_rows)
            all_summary.append(method_summary)
            all_case_type_metrics.extend(compute_case_type_metrics(method, detailed_rows))
    finally:
        await llm_client.close()

    print_summary(all_summary)
    write_detailed_results(args.detailed_results_csv, all_detailed)
    write_summary_results(args.summary_results_csv, all_summary)
    write_case_type_results(args.case_type_results_csv, all_case_type_metrics)

    print(f"\nDetailed results saved to: {args.detailed_results_csv}")
    print(f"Summary results saved to: {args.summary_results_csv}")
    print(f"Case type results saved to: {args.case_type_results_csv}")

    # Optional: per-category confusion when the model returns predicted_category
    # (currently only qwen_civil prompt version does this).
    has_category_predictions = any(item.predicted_category for item in all_detailed)
    if has_category_predictions:
        category_path = Path(args.detailed_results_csv).with_name("category_confusion.json")
        stats_per_method: dict[str, dict] = {}
        for method in methods:
            method_rows = [r for r in all_detailed if r.method == method]
            cat_stats = compute_category_confusion(method_rows)
            if cat_stats:
                stats_per_method[method] = cat_stats
        category_path.parent.mkdir(parents=True, exist_ok=True)
        with category_path.open("w", encoding="utf-8") as f:
            json.dump(stats_per_method, f, ensure_ascii=False, indent=2)
        print(f"Category confusion saved to: {category_path}")
        for method, stats in stats_per_method.items():
            print(
                f"  {method}: exact_match={stats['exact_match']}/{stats['total_with_prediction']} "
                f"({stats['exact_match_rate']:.3f}); per_cat={stats['per_category_accuracy']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CSV-only benchmark for classic, llm and hybrid moderation approaches."
    )
    parser.add_argument(
        "--texts-csv",
        type=str,
        required=True,
        help="Path to CSV with required columns: text + moderation labels.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for quick debug runs; by default all CSV rows are processed sequentially.",
    )
    parser.add_argument(
        "--methods",
        type=str,
        default="classic,llm,hybrid",
        help="Comma-separated methods: classic,llm,hybrid",
    )
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=1,
        help="Warmup runs per method (not included in summary files).",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Measured runs per method.",
    )
    parser.add_argument(
        "--llm-backend",
        choices=["stub", "real"],
        default="stub",
        help="Use stub for isolated benchmark, real for external LLM endpoint.",
    )
    parser.add_argument(
        "--stub-latency-ms",
        type=float,
        default=0.0,
        help="Artificial per-text latency for stub backend.",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default="http://localhost:1234",
        help="Base URL of external LLM backend.",
    )
    parser.add_argument(
        "--llm-endpoint-path",
        type=str,
        default="/v1/chat/completions",
        help="Endpoint path on LLM backend.",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="llamaguard-7b",
        help="Model name sent to external LLM backend.",
    )
    parser.add_argument(
        "--llm-auth-token",
        type=str,
        default=os.getenv("LM_API_TOKEN"),
        help="Optional bearer token; defaults to LM_API_TOKEN env var.",
    )
    parser.add_argument(
        "--llm-timeout-sec",
        type=float,
        default=30.0,
        help="Timeout for each LLM request in seconds.",
    )
    parser.add_argument(
        "--llm-context-length",
        type=int,
        default=2000,
        help="context_length passed to request body.",
    )
    parser.add_argument(
        "--llm-max-input-chars",
        type=int,
        default=1200,
        help="Max number of chars sent from each text to LLM.",
    )
    parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.0,
        help="temperature passed to request body.",
    )
    parser.add_argument(
        "--llm-max-concurrency",
        type=int,
        default=2,
        help="Max concurrent requests for real LLM backend.",
    )
    parser.add_argument(
        "--llm-prompt-version",
        choices=list(LMStudioGuardClient.PROMPT_VERSIONS),
        default="llamaguard_o6",
        help=(
            "Prompt template + response parser version. "
            "llamaguard_o6 (default, LlamaGuard 7B / O1-O6), "
            "llamaguard_s13 (Llama Guard 3, S1-S13), "
            "shieldgemma (Yes/No), "
            "qwen_civil (Qwen2.5 with custom prompt + JSON {label, category})."
        ),
    )
    parser.add_argument(
        "--llm-system-prompt",
        type=str,
        default="",
        help=(
            "Optional system prompt sent as the first message. "
            "Empty by default for guard models. "
            "For qwen_civil a sensible default is auto-injected if left empty."
        ),
    )
    parser.add_argument(
        "--detailed-results-csv",
        type=str,
        default="detailed_results.csv",
        help="Output file for per-sample benchmark results.",
    )
    parser.add_argument(
        "--summary-results-csv",
        type=str,
        default="summary_results.csv",
        help="Output file for aggregate benchmark results.",
    )
    parser.add_argument(
        "--case-type-results-csv",
        type=str,
        default="case_type_results.csv",
        help="Output file with per-case-type quality metrics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.runs <= 0:
        raise ValueError("--runs must be > 0")
    if args.warmup_runs < 0:
        raise ValueError("--warmup-runs must be >= 0")
    if args.llm_max_input_chars <= 0:
        raise ValueError("--llm-max-input-chars must be > 0")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be > 0 when provided")

    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
