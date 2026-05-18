"""Build a balanced sample from civil_comments_train.csv.

Examples:
    # smoke test (50 rows)
    python scripts/build_smoke_sample.py

    # large benchmark sample (4900 rows, 700 per bucket)
    python scripts/build_smoke_sample.py --total 4900 --per-bucket 700 \\
        --output data/benchmark_sample_4900.csv --max-len 600
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

LABEL_COLUMNS = [
    "toxicity",
    "severe_toxicity",
    "obscene",
    "threat",
    "insult",
    "identity_attack",
    "sexual_explicit",
]


def primary_case_type(row: dict[str, str]) -> str:
    def f(name: str) -> float:
        try:
            return float(row.get(name, "") or 0.0)
        except ValueError:
            return 0.0

    if not any(f(c) > 0.0 for c in LABEL_COLUMNS):
        return "clean"
    if f("threat") > 0.0:
        return "threat"
    if f("sexual_explicit") > 0.0:
        return "sexual_explicit"
    if f("identity_attack") > 0.0:
        return "identity_attack"
    if f("obscene") > 0.0:
        return "obscene"
    if f("severe_toxicity") > 0.0:
        return "severe_toxicity"
    if f("insult") > 0.0:
        return "insult"
    return "harmful"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="../civil_comments_train.csv")
    parser.add_argument("--output", type=str, default="../data/smoke_sample_50.csv")
    parser.add_argument("--per-bucket", type=int, default=7,
                        help="Rows per case type (clean takes the rest up to total).")
    parser.add_argument("--total", type=int, default=50)
    parser.add_argument("--max-len", type=int, default=400,
                        help="Skip very long comments to speed up LLM smoke test.")
    parser.add_argument("--min-len", type=int, default=15,
                        help="Skip too-short comments which are noisy.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    target_buckets = {
        "insult": args.per_bucket,
        "obscene": args.per_bucket,
        "identity_attack": args.per_bucket,
        "threat": args.per_bucket,
        "sexual_explicit": args.per_bucket,
        "severe_toxicity": args.per_bucket,
    }
    clean_target = args.total - sum(target_buckets.values())
    target_buckets["clean"] = max(clean_target, 0)

    print(f"Target buckets: {target_buckets}")

    pools: dict[str, list[dict[str, str]]] = {k: [] for k in target_buckets}
    fieldnames: list[str] = []

    # Pool must be >= per_bucket so we can actually pick that many rows.
    target_pool_size = max(500, args.per_bucket * 2)
    seen = 0
    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            seen += 1
            text = (row.get("text") or "").strip()
            if not text:
                continue
            if not (args.min_len <= len(text) <= args.max_len):
                continue
            ctype = primary_case_type(row)
            if ctype not in target_buckets:
                continue
            bucket = pools[ctype]
            if len(bucket) < target_pool_size:
                bucket.append(row)
            else:
                # Reservoir-style replacement to avoid bias toward early rows.
                idx = random.randint(0, seen)
                if idx < target_pool_size:
                    bucket[idx] = row

            if seen % 200_000 == 0:
                sizes = {k: len(v) for k, v in pools.items()}
                print(f"  scanned {seen:>9,} rows | pool sizes: {sizes}")

    print(f"Total scanned: {seen:,}")
    print("Final pool sizes:", {k: len(v) for k, v in pools.items()})

    selected: list[dict[str, str]] = []
    for ctype, target in target_buckets.items():
        pool = pools[ctype]
        random.shuffle(pool)
        picked = pool[:target]
        if len(picked) < target:
            print(f"  WARN: only {len(picked)} rows for bucket '{ctype}' (wanted {target})")
        for row in picked:
            row["_primary_case_type"] = ctype
            selected.append(row)

    random.shuffle(selected)

    out_fieldnames = list(fieldnames) + ["_primary_case_type"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        for row in selected:
            writer.writerow(row)

    final_dist: dict[str, int] = {}
    for row in selected:
        final_dist[row["_primary_case_type"]] = final_dist.get(row["_primary_case_type"], 0) + 1
    print(f"\nSaved {len(selected)} rows to {out_path}")
    print(f"Distribution: {final_dist}")


if __name__ == "__main__":
    main()
