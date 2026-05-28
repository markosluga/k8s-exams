#!/usr/bin/env python3
# Copyright (c) 2026 markosluga
# Licensed under the Apache License, Version 2.0
"""
build_kcna_questions.py
Merges yaml_questions_raw.json and strings_questions_raw.json into
data/kcna/questions.json, deduplicating by normalized question text
and assigning sequential kcna-NNN IDs.

Usage: python tests/build_kcna_questions.py [--dry-run]
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
DATA_DIR = SCRIPT_DIR / "data" / "kcna"
RAW_YAML = DATA_DIR / "yaml_questions_raw.json"
RAW_STRINGS = DATA_DIR / "strings_questions_raw.json"
OUTPUT = DATA_DIR / "questions.json"

FALLBACK_URL = "https://kubernetes.io/docs/home/"


def normalize_text(text: str) -> str:
    """Normalize question text for deduplication comparison."""
    text = text.lower().strip()
    text = re.sub(r'[`*_~]', '', text)          # strip markdown emphasis
    text = re.sub(r'\s+', ' ', text)             # collapse whitespace
    text = re.sub(r'[^\w\s]', '', text)          # strip punctuation
    return text


def clean_option(text: str) -> str:
    """Strip option prefix chars and whitespace."""
    return text.strip().lstrip('.)').strip()


def ensure_explanation(q: dict) -> str:
    """Ensure explanation is at least 50 chars, building from options if needed."""
    expl = q.get("explanation", "").strip()
    if len(expl) >= 50:
        return expl
    # Pad with context from options
    opts = q.get("options", {})
    answer = q.get("answer", "")
    parts = []
    if answer in opts:
        parts.append(f"The correct answer is {answer}: {opts[answer]}.")
    for k, v in opts.items():
        if k != answer:
            parts.append(f"{k}: {v}.")
    combined = expl + " " + " ".join(parts)
    return combined.strip()[:500]


def ensure_doc_link(q: dict) -> str:
    """Return doc_link, falling back to FALLBACK_URL if empty/invalid."""
    link = q.get("doc_link", "").strip()
    if link.startswith("http"):
        return link
    links = q.get("doc_links", [])
    for l in links:
        if isinstance(l, str) and l.startswith("http"):
            return l
    return FALLBACK_URL


def load_raw(path: Path, source_label: str) -> list[dict]:
    if not path.exists():
        print(f"  WARNING: {path} not found, skipping {source_label}")
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} questions from {source_label}")
    return data


def main(dry_run: bool = False) -> int:
    print("=" * 60)
    print("KCNA Questions Builder")
    print("=" * 60)

    yaml_qs = load_raw(RAW_YAML, "yaml_questions_raw.json")
    string_qs = load_raw(RAW_STRINGS, "strings_questions_raw.json")

    if not yaml_qs and not string_qs:
        print("ERROR: No source files found. Run the raw extraction scripts first.")
        return 1

    # Combine: yaml questions first (richer explanations), then strings questions
    all_raw = yaml_qs + string_qs

    # Deduplicate by normalized question text, first-seen wins
    seen_norm: dict[str, int] = {}   # norm_text -> index in final list
    final: list[dict] = []

    skipped_dup = 0
    skipped_invalid = 0

    for q in all_raw:
        question_text = q.get("question", "").strip()
        if not question_text:
            skipped_invalid += 1
            continue

        opts = q.get("options", {})
        if not all(k in opts for k in ("A", "B", "C", "D")):
            skipped_invalid += 1
            continue

        answer = str(q.get("answer", "")).strip().upper()
        if answer not in ("A", "B", "C", "D"):
            skipped_invalid += 1
            continue

        norm = normalize_text(question_text)
        if norm in seen_norm:
            skipped_dup += 1
            continue

        seen_norm[norm] = len(final)
        final.append(q)

    print(f"\n  Total raw       : {len(all_raw)}")
    print(f"  Duplicates      : {skipped_dup}")
    print(f"  Invalid/skipped : {skipped_invalid}")
    print(f"  Unique questions: {len(final)}")

    # Assign sequential kcna-NNN IDs and normalize schema
    output_list = []
    for i, q in enumerate(final, start=1):
        qid = f"kcna-{i:03d}"

        opts = {k: clean_option(str(v)) for k, v in q.get("options", {}).items()}
        answer = str(q.get("answer", "")).strip().upper()

        explanation = ensure_explanation({**q, "options": opts})
        doc_link = ensure_doc_link(q)

        difficulty = str(q.get("difficulty", "medium")).strip().lower()
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"

        domain = str(q.get("domain", "Kubernetes Fundamentals")).strip()
        if not domain:
            domain = "Kubernetes Fundamentals"

        out = {
            "id": qid,
            "domain": domain,
            "difficulty": difficulty,
            "question": q.get("question", "").strip(),
            "options": opts,
            "answer": answer,
            "explanation": explanation,
            "doc_link": doc_link,
            "llm_validated": 0,
        }
        output_list.append(out)

    print(f"\n  Writing {len(output_list)} questions to {OUTPUT}")

    if not dry_run:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(output_list, f, indent=2, ensure_ascii=False)
        print("  Done.")
    else:
        print("  [dry-run] No file written.")
        print("\nSample first 3 questions:")
        for q in output_list[:3]:
            print(json.dumps(q, indent=2)[:300])

    print("=" * 60)
    return 0


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sys.exit(main(dry_run=dry))
