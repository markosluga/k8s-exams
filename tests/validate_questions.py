#!/usr/bin/env python3
# Copyright (c) 2026 markosluga
# Licensed under the Apache License, Version 2.0

"""
Validates all question files across all available exam data directories.

Checks per question:
  - Schema: required fields present with correct types
  - Options: exactly keys A, B, C, D
  - Answer: answer key exists in options
  - Difficulty: one of easy / medium / hard
  - ID format: <exam>-NNN (e.g. kcsa-001)
  - Explanation: non-empty, at least 50 characters
  - doc_link: URL is reachable (HTTP 200)

Global checks:
  - No duplicate IDs within or across files
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# ── constants ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.parent
DATA_DIR = SCRIPT_DIR / "data"

REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "domain": str,
    "difficulty": str,
    "question": str,
    "options": dict,
    "answer": str,
    "explanation": str,
    "doc_link": str,
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_OPTIONS_KEYS = {"A", "B", "C", "D"}
MIN_EXPLANATION_LEN = 50
URL_TIMEOUT = 8  # seconds

# ── result types ─────────────────────────────────────────────────────────────

@dataclass
class Issue:
    severity: str          # "ERROR" | "WARNING"
    check: str
    detail: str

@dataclass
class QuestionResult:
    qid: str
    source_file: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "ERROR" for i in self.issues)

# ── validation helpers ────────────────────────────────────────────────────────

def check_schema(q: dict, result: QuestionResult) -> None:
    for field_name, expected_type in REQUIRED_FIELDS.items():
        if field_name not in q:
            result.issues.append(Issue("ERROR", "schema", f"missing field '{field_name}'"))
        elif not isinstance(q[field_name], expected_type):
            actual = type(q[field_name]).__name__
            result.issues.append(Issue(
                "ERROR", "schema",
                f"field '{field_name}' expected {expected_type.__name__}, got {actual}"
            ))


def check_options(q: dict, result: QuestionResult) -> None:
    opts = q.get("options")
    if not isinstance(opts, dict):
        return  # already caught by schema
    if set(opts.keys()) != VALID_OPTIONS_KEYS:
        result.issues.append(Issue(
            "ERROR", "options",
            f"options keys must be exactly A,B,C,D — got {sorted(opts.keys())}"
        ))
    for key, value in opts.items():
        if not isinstance(value, str) or not value.strip():
            result.issues.append(Issue("ERROR", "options", f"option '{key}' is empty or not a string"))


def check_answer(q: dict, result: QuestionResult) -> None:
    opts = q.get("options")
    answer = q.get("answer")
    if not isinstance(answer, str) or not isinstance(opts, dict):
        return  # covered by schema check
    if answer not in opts:
        result.issues.append(Issue(
            "ERROR", "answer",
            f"answer '{answer}' not in options keys {sorted(opts.keys())}"
        ))


def check_difficulty(q: dict, result: QuestionResult) -> None:
    diff = q.get("difficulty")
    if isinstance(diff, str) and diff not in VALID_DIFFICULTIES:
        result.issues.append(Issue(
            "ERROR", "difficulty",
            f"'{diff}' is not one of {sorted(VALID_DIFFICULTIES)}"
        ))


def check_id_format(q: dict, exam_key: str, result: QuestionResult) -> None:
    qid = q.get("id", "")
    pattern = rf"^{re.escape(exam_key)}-\d{{3,}}$"
    if not re.match(pattern, qid):
        result.issues.append(Issue(
            "ERROR", "id_format",
            f"id '{qid}' does not match expected pattern '{exam_key}-NNN'"
        ))


def check_explanation(q: dict, result: QuestionResult) -> None:
    expl = q.get("explanation", "")
    if not isinstance(expl, str) or len(expl.strip()) < MIN_EXPLANATION_LEN:
        result.issues.append(Issue(
            "WARNING", "explanation",
            f"explanation is too short ({len(expl.strip())} chars, minimum {MIN_EXPLANATION_LEN})"
        ))


def check_url(q: dict, result: QuestionResult) -> None:
    url = q.get("doc_link", "")
    if not isinstance(url, str) or not url.startswith("http"):
        result.issues.append(Issue("ERROR", "doc_link", f"'{url}' is not a valid URL"))
        return
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "k8s-exam-validator/1.0"})
        with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as resp:
            status = resp.status
        if status != 200:
            result.issues.append(Issue("WARNING", "doc_link", f"HTTP {status} for {url}"))
    except urllib.error.HTTPError as e:
        result.issues.append(Issue("ERROR", "doc_link", f"HTTP {e.code} for {url}"))
    except urllib.error.URLError as e:
        result.issues.append(Issue("ERROR", "doc_link", f"unreachable — {e.reason} — {url}"))
    except Exception as e:
        result.issues.append(Issue("ERROR", "doc_link", f"fetch failed — {e} — {url}"))


# ── per-question runner ───────────────────────────────────────────────────────

def validate_question(q: Any, exam_key: str, source_file: str) -> QuestionResult:
    qid = q.get("id", "<unknown>") if isinstance(q, dict) else "<invalid>"
    result = QuestionResult(qid=qid, source_file=source_file)

    if not isinstance(q, dict):
        result.issues.append(Issue("ERROR", "schema", "question is not a JSON object"))
        return result

    check_schema(q, result)
    check_options(q, result)
    check_answer(q, result)
    check_difficulty(q, result)
    check_id_format(q, exam_key, result)
    check_explanation(q, result)
    check_url(q, result)  # network call — last

    return result


# ── file-level runner ─────────────────────────────────────────────────────────

def validate_file(questions_file: Path, exam_key: str) -> list[QuestionResult]:
    try:
        with open(questions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fake = QuestionResult(qid="<parse_error>", source_file=str(questions_file))
        fake.issues.append(Issue("ERROR", "json_parse", str(e)))
        return [fake]
    except OSError as e:
        fake = QuestionResult(qid="<file_error>", source_file=str(questions_file))
        fake.issues.append(Issue("ERROR", "file_read", str(e)))
        return [fake]

    if not isinstance(data, list):
        fake = QuestionResult(qid="<structure>", source_file=str(questions_file))
        fake.issues.append(Issue("ERROR", "structure", "top-level JSON must be an array"))
        return [fake]

    results = []
    for i, q in enumerate(data):
        print(f"  [{exam_key}] validating {i+1}/{len(data)} ...", end="\r", flush=True)
        results.append(validate_question(q, exam_key, str(questions_file)))
    print()  # newline after progress line
    return results


# ── duplicate ID check ────────────────────────────────────────────────────────

def flag_duplicates(all_results: list[QuestionResult]) -> None:
    seen: dict[str, str] = {}  # id -> source_file
    for r in all_results:
        if r.qid in ("<unknown>", "<invalid>", "<parse_error>", "<file_error>", "<structure>"):
            continue
        if r.qid in seen:
            r.issues.insert(0, Issue(
                "ERROR", "duplicate_id",
                f"duplicate of id already seen in {seen[r.qid]}"
            ))
        else:
            seen[r.qid] = r.source_file


# ── report ────────────────────────────────────────────────────────────────────

def print_report(all_results: list[QuestionResult]) -> int:
    error_count = 0
    warning_count = 0
    failed_questions = [r for r in all_results if not r.passed]
    warning_only = [r for r in all_results if r.passed and r.issues]

    # header
    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed and not r.issues)
    print("\n" + "=" * 72)
    print("QUESTION VALIDATION REPORT")
    print("=" * 72)
    print(f"Total questions : {total}")
    print(f"Clean passes    : {passed}")
    print(f"With warnings   : {len(warning_only)}")
    print(f"With errors     : {len(failed_questions)}")
    print("=" * 72)

    # errors section
    if failed_questions:
        print("\n--- ERRORS ---\n")
        for r in failed_questions:
            print(f"  [{r.source_file}]  {r.qid}")
            for issue in r.issues:
                if issue.severity == "ERROR":
                    print(f"    ERROR  [{issue.check}]  {issue.detail}")
                    error_count += 1
            print()

    # warnings section
    if warning_only:
        print("\n--- WARNINGS ---\n")
        for r in warning_only:
            print(f"  [{r.source_file}]  {r.qid}")
            for issue in r.issues:
                print(f"    WARNING  [{issue.check}]  {issue.detail}")
                warning_count += 1
            print()

    # questions that also have both
    mixed = [r for r in failed_questions if any(i.severity == "WARNING" for i in r.issues)]
    if mixed:
        print("\n--- WARNINGS (on failed questions) ---\n")
        for r in mixed:
            for issue in r.issues:
                if issue.severity == "WARNING":
                    print(f"  [{r.source_file}]  {r.qid}  WARNING  [{issue.check}]  {issue.detail}")
                    warning_count += 1
        print()

    print("=" * 72)
    print(f"Total errors   : {error_count}")
    print(f"Total warnings : {warning_count}")
    result_label = "PASS" if error_count == 0 else "FAIL"
    print(f"Result         : {result_label}")
    print("=" * 72 + "\n")

    return error_count


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    if not DATA_DIR.exists():
        print(f"ERROR: data directory not found: {DATA_DIR}")
        return 1

    exam_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    if not exam_dirs:
        print(f"ERROR: no exam subdirectories found in {DATA_DIR}")
        return 1

    all_results: list[QuestionResult] = []

    for exam_dir in sorted(exam_dirs):
        qfile = exam_dir / "questions.json"
        if not qfile.exists():
            print(f"SKIP: {qfile} not found")
            continue
        exam_key = exam_dir.name
        print(f"\nValidating {exam_key} ({qfile}) ...")
        start = time.monotonic()
        results = validate_file(qfile, exam_key)
        elapsed = time.monotonic() - start
        print(f"  done in {elapsed:.1f}s — {len(results)} questions")
        all_results.extend(results)

    flag_duplicates(all_results)
    error_count = print_report(all_results)
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
