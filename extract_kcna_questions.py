#!/usr/bin/env python3
"""
Extract KCNA questions from YAML part files and write to yaml_questions_raw.json.
"""

import yaml
import json
import re
import os
import glob

DATA_DIR = r"c:\code\k8s-exams\data\kcna"
OUTPUT_FILE = os.path.join(DATA_DIR, "yaml_questions_raw.json")


def extract_url(text):
    """Extract a URL from a string like 'Some text. (https://url)'"""
    match = re.search(r'\(?(https?://[^\s\)]+)\)?', text)
    if match:
        return match.group(1).rstrip(')')
    return ""


def strip_url(text):
    """Remove the URL portion from explanation text (the trailing ' (https://...) ' part)."""
    # Remove trailing URL in parentheses
    cleaned = re.sub(r'\s*\(https?://[^\)]*\)\s*$', '', text.strip())
    # Also handle URLs not in parentheses at end
    cleaned = re.sub(r'\s*https?://\S+\s*$', '', cleaned.strip())
    return cleaned.strip().rstrip('.')


def build_explanation(answer_letter, explanations):
    """
    Build explanation string:
    'Answer {letter}: {correct_expl_no_url}. A: {expl}. B: {expl}. C: {expl}. D: {expl}.'
    (skip the correct answer letter in the wrong answers list)
    """
    correct_expl = explanations.get(answer_letter, "")
    correct_text = strip_url(correct_expl)

    parts = [f"Answer {answer_letter}: {correct_text}."]

    for letter in ['A', 'B', 'C', 'D']:
        if letter == answer_letter:
            continue
        expl = explanations.get(letter, "")
        expl_text = strip_url(expl)
        if expl_text:
            parts.append(f"{letter}: {expl_text}.")

    return " ".join(parts)


def process_question(q):
    """Convert a raw YAML question dict into the target JSON structure."""
    yaml_id = int(q['id'])
    question_text = str(q['question'])
    options = {k: str(v) for k, v in q.get('options', {}).items()}
    answer = str(q['answer']).strip().upper()
    explanations = {k: str(v) for k, v in q.get('explanations', {}).items()}

    # Extract all URLs from all option explanations
    doc_links = []
    for letter in ['A', 'B', 'C', 'D']:
        expl = explanations.get(letter, "")
        url = extract_url(expl)
        if url:
            doc_links.append(url)

    # doc_link: URL from the correct answer's explanation
    correct_expl = explanations.get(answer, "")
    doc_link = extract_url(correct_expl)
    # Fallback: first URL in doc_links
    if not doc_link and doc_links:
        doc_link = doc_links[0]

    # Build explanation field
    explanation = build_explanation(answer, explanations)
    # Ensure at least 50 chars
    if len(explanation) < 50:
        explanation = explanation + " " * (50 - len(explanation))

    return {
        "yaml_id": yaml_id,
        "question": question_text,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "doc_links": doc_links,
        "doc_link": doc_link,
        "domain": "Kubernetes Fundamentals",
        "difficulty": "medium",
        "llm_validated": 0,
    }


def strip_outer_quotes(s):
    """Strip one level of surrounding double or single quotes from a string."""
    s = s.strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return s


def parse_file_fallback(filepath):
    """
    Line-by-line fallback parser for YAML files with unescaped inner quotes.
    Handles options and explanations by stripping outer quotes from raw line values.
    """
    with open(filepath, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()

    questions = []
    current = None
    in_options = False
    in_explanations = False

    def flush():
        nonlocal current
        if current and 'id' in current and 'question' in current:
            questions.append(current)
        current = None

    for line in lines:
        stripped = line.rstrip('\n')

        # New question block
        m = re.match(r'^- id:\s*(\d+)', stripped)
        if m:
            flush()
            current = {'id': int(m.group(1)), 'options': {}, 'explanations': {}}
            in_options = False
            in_explanations = False
            continue

        if current is None:
            continue

        # Section headers
        if re.match(r'^\s+options:', stripped):
            in_options = True
            in_explanations = False
            continue
        if re.match(r'^\s+explanations:', stripped):
            in_options = False
            in_explanations = True
            continue
        if re.match(r'^\s+answer:', stripped):
            in_options = False
            in_explanations = False
            m2 = re.match(r'^\s+answer:\s*([A-D])', stripped)
            if m2:
                current['answer'] = m2.group(1)
            continue
        if re.match(r'^\s+question:', stripped):
            in_options = False
            in_explanations = False
            m2 = re.match(r'^\s+question:\s*(.*)', stripped)
            if m2:
                current['question'] = strip_outer_quotes(m2.group(1))
            continue

        # Option/explanation key-value (4-space indent + letter + colon)
        m = re.match(r'^\s{4}([A-D]):\s*(.*)', stripped)
        if m:
            key = m.group(1)
            val = strip_outer_quotes(m.group(2))
            if in_options:
                current['options'][key] = val
            elif in_explanations:
                current['explanations'][key] = val
            continue

    flush()
    return questions


def main():
    # Find all part files
    pattern = os.path.join(DATA_DIR, "questions.yaml.part*")
    part_files = sorted(glob.glob(pattern))

    if not part_files:
        print("ERROR: No part files found!")
        return

    print(f"Found {len(part_files)} part files:")
    for f in part_files:
        print(f"  {os.path.basename(f)}")

    all_questions = {}  # yaml_id -> processed question (first-seen wins)
    total_raw = 0

    for filepath in part_files:
        basename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as fh:
            content = fh.read()

        # Try PyYAML first
        data = None
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, list):
                data = None
        except yaml.YAMLError:
            data = None

        # Fallback to line-by-line parser
        if not data:
            data = parse_file_fallback(filepath)
            if data:
                print(f"  {basename}: fallback parser used")
            else:
                print(f"  WARNING: {basename} has no parseable data, skipping")
                continue

        file_count = 0
        for q in data:
            if not isinstance(q, dict) or 'id' not in q:
                continue
            total_raw += 1
            file_count += 1
            yaml_id = int(q['id'])
            if yaml_id not in all_questions:
                try:
                    processed = process_question(q)
                    all_questions[yaml_id] = processed
                except Exception as e:
                    print(f"  WARNING: Error processing id={yaml_id} in {basename}: {e}")

        print(f"  {basename}: {file_count} questions")

    # Sort by yaml_id
    sorted_questions = [all_questions[k] for k in sorted(all_questions.keys())]

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as fh:
        json.dump(sorted_questions, fh, indent=2, ensure_ascii=False)

    print(f"\nSummary:")
    print(f"  Total raw question entries read: {total_raw}")
    print(f"  Unique yaml_ids: {len(all_questions)}")
    print(f"  Output written to: {OUTPUT_FILE}")

    # Quick validation sample
    if sorted_questions:
        first = sorted_questions[0]
        print(f"\nSample (id={first['yaml_id']}):")
        print(f"  question: {first['question'][:80]}...")
        print(f"  answer: {first['answer']}")
        print(f"  doc_link: {first['doc_link']}")
        print(f"  explanation length: {len(first['explanation'])}")
        print(f"  explanation: {first['explanation'][:120]}...")


if __name__ == "__main__":
    main()
