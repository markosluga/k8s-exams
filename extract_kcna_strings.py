#!/usr/bin/env python3
# Copyright (c) 2026 markosluga
# Licensed under the Apache License, Version 2.0
"""
extract_kcna_strings.py
Recovers KCNA questions from .local/kcna_strings.txt and
.local/kcna_strings_100plus.txt (accidental-deletion recovery).

Strategy:
  1. Read each file, join ALL file lines (removing real newlines) into one blob
  2. Replace literal \n (2-char JSON escape) with actual newlines
  3. Find all ### kcna-NNN sections via regex
  4. Parse each section
  5. Dedup by kcna-ID (first-seen wins)
  6. Write to data/kcna/strings_questions_raw.json
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOCAL_DIR = SCRIPT_DIR / ".local"
DATA_DIR = SCRIPT_DIR / "data" / "kcna"
OUTPUT = DATA_DIR / "strings_questions_raw.json"

FALLBACK_URL = "https://kubernetes.io/docs/home/"


def reconstruct_text(filepath: Path) -> str:
    """Join all file lines (stripping real newlines) then unescape \\n."""
    raw = filepath.read_text(encoding="utf-8", errors="replace")
    # Remove actual file newlines (content was split at arbitrary points)
    joined = raw.replace("\r\n", "").replace("\n", "")
    # Un-escape JSON-escaped newlines → real newlines
    # Also un-escape other common JSON escape sequences
    joined = joined.replace("\\n", "\n")
    joined = joined.replace("\\t", "\t")
    joined = joined.replace('\\"', '"')
    joined = joined.replace("\\'", "'")
    return joined


def extract_url_from_reference(ref_text: str) -> str:
    """Extract URL from **Reference:** or **Doc Link:** line."""
    # Markdown link: [text](url)
    m = re.search(r'\[.*?\]\((https?://[^\)]+)\)', ref_text)
    if m:
        return m.group(1).strip()
    # Plain URL
    m = re.search(r'(https?://\S+)', ref_text)
    if m:
        url = m.group(1).rstrip('.,)')
        return url
    return ""


def parse_option_text(raw: str) -> str:
    """Clean up option text: strip leading letter+paren/dot, backtick markers."""
    s = raw.strip()
    # Remove trailing markdown spaces/newlines
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def parse_question_block(block: str, kcna_id: str) -> dict | None:
    """
    Parse a single question block (text between ### kcna-NNN and next section).
    Returns a dict or None if parsing fails.
    """
    lines = block.split("\n")

    domain = "Kubernetes Fundamentals"
    difficulty = "medium"
    question = ""
    options: dict[str, str] = {}
    answer = ""
    explanation = ""
    doc_link = ""

    in_question = False
    current_option = None

    for line in lines:
        line_s = line.strip()

        # Domain
        m = re.match(r'\*\*Domain:\*\*\s*(.+)', line_s)
        if m:
            domain = m.group(1).strip().rstrip('\\').strip()
            continue

        # Difficulty
        m = re.match(r'\*\*Difficulty:\*\*\s*(.+)', line_s, re.IGNORECASE)
        if m:
            difficulty = m.group(1).strip().rstrip('\\').strip().lower()
            continue

        # Question
        m = re.match(r'\*\*Question:\*\*\s*(.*)', line_s)
        if m:
            question = m.group(1).strip()
            in_question = True
            current_option = None
            continue

        # Answer line
        m = re.match(r'\*\*Answer:\*\*\s*([A-D])', line_s)
        if m:
            answer = m.group(1).strip()
            in_question = False
            current_option = None
            continue

        # Explanation
        m = re.match(r'\*\*Explanation:\*\*\s*(.*)', line_s)
        if m:
            explanation = m.group(1).strip()
            in_question = False
            current_option = None
            continue

        # Doc Link / Reference
        m = re.match(r'\*\*(?:Doc Link|Reference):\*\*\s*(.*)', line_s)
        if m:
            ref_raw = m.group(1).strip()
            doc_link = extract_url_from_reference(ref_raw)
            in_question = False
            current_option = None
            continue

        # Option line: A. / A) / A:
        m = re.match(r'^([A-D])[.)]\s*(.*)', line_s)
        if m:
            key = m.group(1)
            val = parse_option_text(m.group(2))
            # Handle "A) text  \" trailing slash
            val = val.rstrip('\\').strip()
            options[key] = val
            current_option = key
            in_question = False
            continue

        # Continuation lines
        if line_s and not line_s.startswith('**') and not line_s.startswith('#') and not line_s.startswith('---'):
            if in_question and question:
                question = (question + " " + line_s).strip()
            elif current_option and current_option in options:
                options[current_option] = (options[current_option] + " " + line_s.rstrip('\\').strip()).strip()

    # Validate
    if not question or not answer or answer not in "ABCD":
        return None
    if len(options) < 4 or not all(k in options for k in ("A", "B", "C", "D")):
        return None

    # Build explanation
    if not explanation:
        explanation = f"Answer {answer}: {options.get(answer, '')}."

    # Ensure min length
    if len(explanation.strip()) < 50:
        opts_text = " ".join(f"{k}: {v}." for k, v in options.items() if k != answer)
        explanation = (explanation + " " + opts_text).strip()

    return {
        "id": kcna_id,
        "domain": domain,
        "difficulty": difficulty if difficulty in ("easy", "medium", "hard") else "medium",
        "question": question.strip(),
        "options": options,
        "answer": answer.upper(),
        "explanation": explanation.strip(),
        "doc_link": doc_link if doc_link.startswith("http") else FALLBACK_URL,
        "llm_validated": 0,
    }


def extract_from_file(filepath: Path) -> dict[str, dict]:
    """Return dict of kcna_id -> question dict, deduped by ID."""
    print(f"\n  Processing {filepath.name} ...")
    text = reconstruct_text(filepath)

    # Find all ### kcna-NNN sections
    # Split on the ### kcna- header pattern
    parts = re.split(r'###\s+kcna-(\d+)\s*\n', text)

    # parts: [pre_text, id1, block1, id2, block2, ...]
    results: dict[str, dict] = {}
    i = 1
    while i < len(parts) - 1:
        raw_id = parts[i].strip()
        block = parts[i + 1]
        # Trim block at next section boundary (---, ### ) if visible
        block = re.split(r'\n---\n', block)[0]
        i += 2

        num = int(raw_id)
        kcna_id = f"kcna-{num:03d}"

        if kcna_id in results:
            continue  # first-seen wins

        parsed = parse_question_block(block, kcna_id)
        if parsed:
            results[kcna_id] = parsed
        else:
            print(f"    WARN: could not parse {kcna_id}")

    print(f"  Extracted {len(results)} questions from {filepath.name}")
    return results


def main():
    print("=" * 60)
    print("KCNA Strings Recovery")
    print("=" * 60)

    all_questions: dict[str, dict] = {}

    for fname in ("kcna_strings.txt", "kcna_strings_100plus.txt"):
        path = LOCAL_DIR / fname
        if not path.exists():
            print(f"  SKIP: {fname} not found")
            continue
        extracted = extract_from_file(path)
        # Merge (first-seen from kcna_strings.txt wins over 100plus for same IDs)
        for qid, q in extracted.items():
            if qid not in all_questions:
                all_questions[qid] = q

    # Sort by numeric kcna ID
    sorted_list = sorted(all_questions.values(), key=lambda q: int(q["id"].split("-")[1]))

    print(f"\n  Total unique questions recovered: {len(sorted_list)}")
    if sorted_list:
        ids = [q["id"] for q in sorted_list]
        print(f"  ID range: {ids[0]} → {ids[-1]}")
        print(f"  IDs: {', '.join(ids[:10])}{'...' if len(ids) > 10 else ''}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted_list, f, indent=2, ensure_ascii=False)

    print(f"\n  Written to {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
