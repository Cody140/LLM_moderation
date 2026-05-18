import asyncio
import re

from app.moderators.base import (
    BatchModerationResponse,
    ModerationResult,
    ModerationSummary,
)


class ClassicModerator:
    """Baseline rule-based moderator.

    This module is intentionally simple and deterministic for benchmark reproducibility.
    It is not meant to replace context-aware moderation.
    """

    def __init__(self) -> None:
        self._hard_blacklist = {
            "idiot",
            "stupid",
            "moron",
            "hate",
            "kill",
            "trash",
            "loser",
            "bitch",
            "dumb",
        }
        self._soft_suspicious = {
            "sucks",
            "shut",
            "damn",
            "hell",
            "nobody",
            "worthless",
        }

        self._char_map = {
            "@": "a",
            "4": "a",
            "0": "o",
            "1": "i",
            "|": "i",
            "3": "e",
            "6": "g",
            "7": "t",
            "8": "b",
            "9": "g",
            "2": "z",
            "$": "s",
            "5": "s",
            "+": "t",
        }

        self._regex_patterns = {
            "threat_pattern": re.compile(r"\b(i\s*will\s*kill\s*you|kill\s*you)\b", re.IGNORECASE),
            "insult_pattern": re.compile(r"\b(you\s+are\s+(an?\s+)?(idiot|moron|loser|stupid))\b", re.IGNORECASE),
            "hate_pattern": re.compile(r"\b(i\s+hate\s+you|hate\s+you)\b", re.IGNORECASE),
            "obfuscated_insult": re.compile(r"\b(id[i1!|]ot|st[u*]pid|m[o0]ron)\b", re.IGNORECASE),
        }

    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        return await asyncio.to_thread(self._moderate_sync, texts)

    def _moderate_sync(self, texts: list[str]) -> BatchModerationResponse:
        results = [self._moderate_one(text) for text in texts]

        total = len(results)
        flagged = sum(1 for item in results if item.status == "ok" and bool(item.violation))
        clean = sum(1 for item in results if item.status == "ok" and item.violation is False)
        processing_errors = total - (flagged + clean)
        rate = flagged / total if total else 0.0
        error_rate = processing_errors / total if total else 0.0

        return BatchModerationResponse(
            method="classic",
            results=results,
            summary=ModerationSummary(
                total_texts=total,
                flagged_texts=flagged,
                clean_texts=clean,
                violation_rate=rate,
                processed_ok=flagged + clean,
                processing_errors=processing_errors,
                error_rate=error_rate,
            ),
        )

    def _moderate_one(self, text: str) -> ModerationResult:
        normalized, obfuscation_detected = self._normalize_text(text)

        matched_rules: list[str] = []
        matched_rules.extend(self._check_blacklist(normalized))
        matched_rules.extend(self._check_regex(text))
        matched_rules.extend(self._check_rules(normalized, text))

        score = float(len(matched_rules))
        decision_type = self._decide_type(normalized, matched_rules)
        decision_reason = self._build_decision_reason(matched_rules, obfuscation_detected)
        if decision_type == "violation":
            violation = True
        elif decision_type == "clean":
            violation = False
        else:
            violation = False

        return ModerationResult(
            text=text,
            violation=violation,
            score=score,
            matched_rules=matched_rules,
            details={
                "normalized_text": normalized,
                "obfuscation_detected": obfuscation_detected,
                "decision_reason": decision_reason,
            },
            status="ok",
            decision_type=decision_type,
            route="classic_only",
            decision_reason=decision_reason,
        )

    def _normalize_text(self, text: str) -> tuple[str, bool]:
        text = text.strip().lower()
        obfuscation_detected = False
        for old, new in self._char_map.items():
            if old in text:
                obfuscation_detected = True
                text = text.replace(old, new)

        # Keep alnum and spaces only to stabilize baseline pattern matching.
        text = text.replace("_", " ").replace("-", " ")
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"(.)\1{2,}", r"\1\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text, obfuscation_detected

    def _check_blacklist(self, text: str) -> list[str]:
        return [f"blacklist:{word}" for word in text.split() if word in self._hard_blacklist]

    def _check_regex(self, original_text: str) -> list[str]:
        matched = []
        for name, pattern in self._regex_patterns.items():
            if pattern.search(original_text):
                matched.append(f"regex:{name}")
        return matched

    def _check_rules(self, normalized_text: str, original_text: str) -> list[str]:
        matched = []

        letters = [ch for ch in original_text if ch.isalpha()]
        if letters:
            upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
            if upper_ratio > 0.7 and len(letters) >= 6:
                matched.append("rule:too_many_caps")

        if original_text.count("!") >= 5:
            matched.append("rule:too_many_exclamations")

        if re.search(r"\byou\b", normalized_text) and re.search(r"\b(idiot|moron|stupid|loser)\b", normalized_text):
            matched.append("rule:direct_insult")

        tokens = set(normalized_text.split())
        if any(word in tokens for word in self._soft_suspicious):
            matched.append("rule:suspicious_soft_signal")

        return matched

    def _decide_type(self, normalized_text: str, matched_rules: list[str]) -> str:
        rule_count = len(matched_rules)
        tokens = set(normalized_text.split())
        hard_hits = len(tokens.intersection(self._hard_blacklist))

        if hard_hits >= 1 and rule_count >= 1:
            return "violation"
        if any(name.startswith("regex:threat_pattern") for name in matched_rules):
            return "violation"
        if any(name.startswith("regex:insult_pattern") for name in matched_rules):
            return "violation"
        if any(name.startswith("regex:hate_pattern") for name in matched_rules):
            return "violation"
        if any(name.startswith("regex:obfuscated_insult") for name in matched_rules):
            return "uncertain"
        if any(name == "rule:suspicious_soft_signal" for name in matched_rules):
            return "uncertain"
        return "clean"

    def _build_decision_reason(self, matched_rules: list[str], obfuscation_detected: bool) -> str:
        if any(rule.startswith("blacklist:") for rule in matched_rules):
            return "rule_blacklist"
        if any(rule.startswith("regex:") for rule in matched_rules):
            return "regex_match"
        if any(rule == "rule:suspicious_soft_signal" for rule in matched_rules):
            return "soft_signal"
        if obfuscation_detected:
            return "obfuscation_detected"
        return "clean_signal"
