"""Generate obfuscated variants of harmful texts for RTU requirement 'maskētus pārkāpumus'.

Takes a benchmark sample CSV, picks harmful rows, applies obfuscation transforms,
and outputs a new CSV with both original and obfuscated versions for comparison.

Obfuscation types:
  leet        - a→@, e→3, i→1, o→0, s→$  (e.g. "hate" → "h@t3")
  asterisk    - vowels replaced with *     (e.g. "fuck" → "f*ck")
  underscore  - spaces replaced with _     (e.g. "kill you" → "kill_you")
  zwsp        - zero-width spaces inserted between chars of sensitive words
  homoglyph   - latin letters replaced with similar Unicode chars (а→а cyrillic, etc.)
  mixed       - combination of leet + zwsp

Usage:
    cd code
    python scripts/build_obfuscated_sample.py
    python scripts/build_obfuscated_sample.py --input data/benchmark_sample_4900.csv \\
        --output data/obfuscated_sample.csv --per-type 100
"""
from __future__ import annotations

import argparse
import csv
import random
import unicodedata
from pathlib import Path

LABEL_COLUMNS = [
    "toxicity", "severe_toxicity", "obscene", "threat",
    "insult", "identity_attack", "sexual_explicit",
]

# Common toxic/profane word fragments to target for obfuscation
_SENSITIVE_WORDS = [
    "hate", "kill", "fuck", "shit", "bitch", "ass", "damn", "crap",
    "idiot", "stupid", "moron", "loser", "ugly", "die", "dead",
    "nigger", "nigga", "faggot", "retard", "whore", "slut",
    "trash", "scum", "filth", "awful", "terrible", "disgusting",
]

_LEET_MAP = str.maketrans("aeiostAEIOST", "@310$7@310$7")

_HOMOGLYPH_MAP = str.maketrans(
    "aAcCeEiIoOpPsS",
    "аАсСеЕіІоОрРѕЅ",
)

ZWSP = "​"  # zero-width space


def _leet(text: str) -> str:
    return text.translate(_LEET_MAP)


def _asterisk(text: str) -> str:
    """Replace internal vowels of each word with *."""
    result = []
    for word in text.split(" "):
        if len(word) > 3:
            chars = list(word)
            for i in range(1, len(chars) - 1):
                if chars[i].lower() in "aeiou":
                    chars[i] = "*"
            result.append("".join(chars))
        else:
            result.append(word)
    return " ".join(result)


def _underscore(text: str) -> str:
    """Replace spaces with underscores."""
    return text.replace(" ", "_")


def _zwsp(text: str) -> str:
    """Insert zero-width spaces between characters of every word longer than 3 chars."""
    words = text.split(" ")
    result = []
    for word in words:
        if len(word) > 3:
            result.append(ZWSP.join(word))
        else:
            result.append(word)
    return " ".join(result)


def _homoglyph(text: str) -> str:
    """Replace some latin chars with visually similar Unicode chars."""
    return text.translate(_HOMOGLYPH_MAP)


def _mixed(text: str) -> str:
    """Combine leet + zwsp."""
    return _zwsp(_leet(text))


OBFUSCATIONS: dict[str, callable] = {
    "leet": _leet,
    "asterisk": _asterisk,
    "underscore": _underscore,
    "zwsp": _zwsp,
    "homoglyph": _homoglyph,
    "mixed": _mixed,
}


def is_harmful(row: dict[str, str]) -> bool:
    for col in LABEL_COLUMNS:
        try:
            if float(row.get(col) or 0) > 0:
                return True
        except ValueError:
            pass
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/benchmark_sample_4900.csv")
    parser.add_argument("--output", default="data/obfuscated_sample.csv")
    parser.add_argument("--per-type", type=int, default=100,
                        help="Number of harmful texts per obfuscation type.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with in_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            rows.append(row)

    harmful = [r for r in rows if is_harmful(r)]
    print(f"Loaded {len(rows)} rows, {len(harmful)} harmful.")

    out_rows: list[dict] = []
    out_fieldnames = fieldnames + ["_obfuscation_type", "_original_text"]

    for obf_name, obf_fn in OBFUSCATIONS.items():
        pool = harmful.copy()
        random.shuffle(pool)
        selected = pool[: args.per_type]
        if len(selected) < args.per_type:
            print(f"  WARN: only {len(selected)} harmful rows (wanted {args.per_type})")

        for row in selected:
            original_text = row["text"]
            obf_text = obf_fn(original_text)
            new_row = dict(row)
            new_row["text"] = obf_text
            new_row["_obfuscation_type"] = obf_name
            new_row["_original_text"] = original_text
            # Mark as harmful (all labels preserved from original)
            out_rows.append(new_row)

    random.shuffle(out_rows)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)

    type_counts: dict[str, int] = {}
    for row in out_rows:
        t = row["_obfuscation_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"Saved {len(out_rows)} obfuscated rows to {out_path}")
    print(f"Distribution by type: {type_counts}")


if __name__ == "__main__":
    main()
