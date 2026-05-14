#!/usr/bin/env python3
# Copyright (c) 2026 markosluga
# Licensed under the Apache License, Version 2.0

"""
LLM-based cognitive assessment of exam questions using the Claude API.
Complements the structural validator (validate_questions.py) with semantic checks.

Evaluates each question for:
  - Answer correctness (is the stated answer definitively best?)
  - Question clarity and unambiguity
  - Distractor quality (plausible but wrong options)
  - Explanation accuracy and educational value
  - Difficulty calibration
  - Domain relevance

llm_validated field in questions.json:
  0 = not yet assessed (will be processed by this script)
  1 = assessed and clean  OR  assessed with issues that were fixed inline
  2 = assessed, issues found that could not be fixed automatically (needs manual edit)

Questions with llm_validated != 0 are skipped. Re-set to 0 to re-assess.
Dated markdown reports in reports/ are the audit trail for all fixes applied.

Usage:
  python tests/llm_assess_questions.py                    # sync, all exams
  python tests/llm_assess_questions.py --exam kcsa        # specific exam
  python tests/llm_assess_questions.py --limit 10         # first N questions only
  python tests/llm_assess_questions.py --batch            # async batch mode (50% cheaper)
  python tests/llm_assess_questions.py --poll BATCH_ID    # fetch + report batch results
  python tests/llm_assess_questions.py --model claude-haiku-4-5

Requires: ANTHROPIC_API_KEY environment variable
Install:  pip install anthropic
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass  # dotenv optional — falls back to environment variable

try:
    import anthropic
except ImportError:
    print("Missing dependency: pip install anthropic python-dotenv")
    sys.exit(1)

# ── constants ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.parent
DATA_DIR = SCRIPT_DIR / "data"
REPORTS_DIR = SCRIPT_DIR / "reports"
DEFAULT_MODEL = "claude-opus-4-7"
BATCH_ID_FILE = SCRIPT_DIR / ".llm_assess_batch_id"

SYSTEM_PROMPT = """You are a senior Kubernetes certification exam designer with deep expertise \
in KCSA, KCNA, CKA, CKAD, and CKS exams. You review multiple-choice questions for technical \
accuracy, pedagogical quality, and exam readiness.

For each question presented as JSON, identify ONLY genuine problems. Do not flag minor \
stylistic preferences or perfectly acceptable phrasing. Apply Kubernetes official documentation \
and CNCF best practices as the ground truth.

Evaluate these six dimensions:

1. answer_correctness — Is the stated answer definitively the BEST answer according to \
official Kubernetes docs and industry consensus? Flag if another option is equally or more \
correct, or if the stated answer is factually wrong.

2. question_clarity — Is the question clear, grammatically correct, and unambiguous? Flag \
confusing phrasing, double negatives, vague "which of the following" without sufficient context, \
or questions where the stem doesn't clearly indicate what's being asked.

3. distractor_quality — Are the incorrect options (distractors) plausible to someone \
unfamiliar with the topic but clearly wrong to an expert? Flag if distractors are trivially \
wrong, if two options are both correct, or if any option is internally contradictory.

4. explanation_accuracy — Is the explanation factually accurate? Flag incorrect statements, \
misleading information, or missing context that would leave a learner with a wrong mental model.

5. difficulty_calibration — Is the stated difficulty (easy/medium/hard) appropriate? Flag \
only clear mismatches: a simple single-concept definition labeled "hard", or a nuanced \
multi-step scenario labeled "easy".

6. domain_relevance — Does the question actually test knowledge from the stated domain? \
Flag questions that test unrelated concepts.

Respond ONLY with a JSON object — no preamble, no explanation outside the JSON.

The response MUST contain two top-level keys:

1. "analysis" — an object with one key per dimension. For EVERY dimension, write 2-5 sentences \
explaining your evaluation: what you checked, what you found, and why it passes or fails. \
Be specific — cite the question text, options, answer, or explanation as evidence. \
Never leave a dimension blank.

2. "issues" — an array of flagged problems. Only include genuine problems, not stylistic nit-picks.

3. "fixes" — present ONLY when "issues" is non-empty. Provide corrected values for every \
field that needs changing, plus a "changes" list describing each correction. Omit fields \
that need no change. If an issue cannot be fixed without deeper domain research, omit that \
field and note it in "changes" so it can be handled manually. If "issues" is empty, omit \
"fixes" entirely.

Example — question with no issues:
{
  "analysis": {
    "answer_correctness": "The stated answer B is correct...",
    "question_clarity": "Clear and unambiguous...",
    "distractor_quality": "All distractors are plausible...",
    "explanation_accuracy": "Explanation is factually accurate...",
    "difficulty_calibration": "Easy is appropriate...",
    "domain_relevance": "Directly tests the stated domain."
  },
  "issues": []
}

Example — question with a fixable encoding artifact:
{
  "analysis": { ... },
  "issues": [
    {"check": "explanation_accuracy", "severity": "warning",
     "detail": "Encoding artifact â€" appears instead of em dash."}
  ],
  "fixes": {
    "explanation": "The 4Cs are Cloud, Cluster, Container, Code — outermost to innermost.",
    "changes": ["Fixed mojibake encoding artifact â€" → — in explanation."]
  }
}

Use "error" severity for correctness and factual problems (wrong answer, false explanation).
Use "warning" severity for quality problems (weak distractors, mild ambiguity, difficulty mismatch)."""

_DIMENSIONS = [
    "answer_correctness",
    "question_clarity",
    "distractor_quality",
    "explanation_accuracy",
    "difficulty_calibration",
    "domain_relevance",
]

ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "object",
            "properties": {dim: {"type": "string"} for dim in _DIMENSIONS},
            "required": _DIMENSIONS,
            "additionalProperties": False,
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "check": {"type": "string", "enum": _DIMENSIONS},
                    "severity": {"type": "string", "enum": ["error", "warning"]},
                    "detail": {"type": "string"},
                },
                "required": ["check", "severity", "detail"],
                "additionalProperties": False,
            },
        },
        "fixes": {
            "type": "object",
            "properties": {
                "changes":     {"type": "array", "items": {"type": "string"}},
                "question":    {"type": "string"},
                "options": {
                    "type": "object",
                    "properties": {k: {"type": "string"} for k in ["A", "B", "C", "D"]},
                    "additionalProperties": False,
                },
                "answer":      {"type": "string", "enum": ["A", "B", "C", "D"]},
                "explanation": {"type": "string"},
                "difficulty":  {"type": "string", "enum": ["easy", "medium", "hard"]},
            },
            "required": ["changes"],
            "additionalProperties": False,
        },
    },
    "required": ["analysis", "issues"],
    "additionalProperties": False,
}

# ── result types ─────────────────────────────────────────────────────────────


@dataclass
class LLMIssue:
    check: str
    severity: str
    detail: str


@dataclass
class AssessmentResult:
    qid: str
    source_file: str
    issues: list[LLMIssue] = field(default_factory=list)
    analysis: dict[str, str] = field(default_factory=dict)
    fixes: dict = field(default_factory=dict)  # corrected field values + changes list
    reasoning: str = ""  # raw thinking blocks from the API
    api_error: str = ""

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


# ── file bank ─────────────────────────────────────────────────────────────────
# A file bank keeps all questions for each source file in memory as mutable
# dicts so we can update llm_validated in-place and write back in one pass.

FileBank = dict[str, list[dict]]


def load_file_bank(exam_filter: str | None) -> FileBank:
    """Load all questions from all matching exam files."""
    bank: FileBank = {}
    if not DATA_DIR.exists():
        return bank
    for exam_dir in sorted(DATA_DIR.iterdir()):
        if not exam_dir.is_dir():
            continue
        if exam_filter and exam_dir.name != exam_filter:
            continue
        qfile = exam_dir / "questions.json"
        if not qfile.exists():
            continue
        with open(qfile, "r", encoding="utf-8") as f:
            data = json.load(f)
        bank[str(qfile)] = [q for q in data if isinstance(q, dict)]
    return bank


def get_unvalidated(bank: FileBank, limit: int | None) -> list[tuple[str, dict]]:
    """Return (filepath, question_dict) refs for questions with llm_validated == 0."""
    unvalidated: list[tuple[str, dict]] = []
    for filepath, questions in bank.items():
        for q in questions:
            if q.get("llm_validated", 0) == 0:
                unvalidated.append((filepath, q))
    if limit:
        unvalidated = unvalidated[:limit]
    return unvalidated


def save_file_bank(bank: FileBank) -> None:
    """Write each question list back to its source file."""
    for filepath, questions in bank.items():
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)


_FIXABLE_FIELDS = {"question", "options", "answer", "explanation", "difficulty"}


def apply_results_to_bank(results: list[AssessmentResult], bank: FileBank) -> None:
    """Update question dicts in the bank based on assessment results.

    Tags:
      1 = clean, no issues
      0 = had issues, fixes applied — reset so assessor re-validates next run
      2 = has issues, no fixes provided — needs manual review
    API errors leave the tag unchanged (stays 0, retried next run).
    """
    index: dict[str, dict] = {}
    for questions in bank.values():
        for q in questions:
            qid = q.get("id")
            if qid:
                index[qid] = q

    for result in results:
        if result.api_error:
            continue
        q = index.get(result.qid)
        if q is None:
            continue

        if not result.has_issues:
            q["llm_validated"] = 1
        elif result.fixes and result.fixes.get("changes"):
            for field in _FIXABLE_FIELDS:
                if field in result.fixes:
                    q[field] = result.fixes[field]
            q["llm_validated"] = 1  # fixed inline during assessment — report is the audit trail
        else:
            q["llm_validated"] = 2  # issues flagged but nothing fixable automatically


def apply_results_to_files(results: list[AssessmentResult]) -> None:
    """Apply results when we don't have a pre-loaded bank (batch --poll path).

    Scans all exam question files to locate each qid, then writes tags back.
    """
    bank = load_file_bank(exam_filter=None)
    apply_results_to_bank(results, bank)
    save_file_bank(bank)


# ── helpers ───────────────────────────────────────────────────────────────────


def build_question_prompt(q: dict) -> str:
    return json.dumps(
        {
            "id": q.get("id"),
            "domain": q.get("domain"),
            "difficulty": q.get("difficulty"),
            "question": q.get("question"),
            "options": q.get("options"),
            "answer": q.get("answer"),
            "explanation": q.get("explanation"),
        },
        ensure_ascii=False,
        indent=2,
    )


def extract_reasoning(content) -> str:
    """Concatenate all thinking blocks from an API response content list."""
    parts = [b.thinking for b in content if getattr(b, "type", None) == "thinking" and b.thinking]
    return "\n\n".join(parts)


def parse_response(text: str) -> tuple[dict[str, str], list[LLMIssue], dict]:
    data = json.loads(text)
    analysis = data.get("analysis", {})
    issues = [
        LLMIssue(check=i["check"], severity=i["severity"], detail=i["detail"])
        for i in data.get("issues", [])
    ]
    fixes = data.get("fixes", {})
    return analysis, issues, fixes


def make_api_params(q: dict, model: str) -> dict:
    """Shared request params for both sync and batch modes."""
    return dict(
        model=model,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": ASSESSMENT_SCHEMA}},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": build_question_prompt(q)}],
    )


# ── sync mode ────────────────────────────────────────────────────────────────


def assess_sync(
    client: anthropic.Anthropic, questions: list[tuple[str, dict]], model: str
) -> list[AssessmentResult]:
    results: list[AssessmentResult] = []
    total = len(questions)

    for idx, (source_file, q) in enumerate(questions, 1):
        qid = q.get("id", f"<unknown-{idx}>")
        print(f"  [{idx}/{total}] {qid} ...", end="\r", flush=True)

        result = AssessmentResult(qid=qid, source_file=source_file)
        try:
            with client.messages.stream(**make_api_params(q, model)) as stream:
                final = stream.get_final_message()
            result.reasoning = extract_reasoning(final.content)
            text = next((b.text for b in final.content if b.type == "text"), "")
            if text:
                result.analysis, result.issues, result.fixes = parse_response(text)
        except anthropic.APIError as e:
            result.api_error = f"API error: {e}"
        except json.JSONDecodeError as e:
            result.api_error = f"JSON parse error: {e}"
        except Exception as e:
            result.api_error = f"Unexpected error: {e}"

        results.append(result)

    print()  # clear progress line
    return results


# ── batch mode ────────────────────────────────────────────────────────────────


def submit_batch(
    client: anthropic.Anthropic, questions: list[tuple[str, dict]], model: str
) -> str:
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    requests = []
    for source_file, q in questions:
        qid = q.get("id", "unknown")
        params = make_api_params(q, model)
        params.pop("stream", None)
        requests.append(
            Request(
                custom_id=qid,  # must match ^[a-zA-Z0-9_-]{1,64}$
                params=MessageCreateParamsNonStreaming(**params),
            )
        )

    batch = client.messages.batches.create(requests=requests)
    return batch.id


def poll_batch(client: anthropic.Anthropic, batch_id: str) -> list[AssessmentResult]:
    print(f"Polling batch {batch_id} ...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f"  Status: {batch.processing_status}  "
            f"processing={counts.processing}  succeeded={counts.succeeded}  "
            f"errored={counts.errored}",
            end="\r",
            flush=True,
        )
        if batch.processing_status == "ended":
            break
        time.sleep(30)
    print()

    results: list[AssessmentResult] = []
    for item in client.messages.batches.results(batch_id):
        qid = item.custom_id
        ar = AssessmentResult(qid=qid, source_file="")

        if item.result.type == "succeeded":
            content = item.result.message.content
            ar.reasoning = extract_reasoning(content)
            text = next((b.text for b in content if b.type == "text"), "")
            if text:
                try:
                    ar.analysis, ar.issues, ar.fixes = parse_response(text)
                except json.JSONDecodeError as e:
                    ar.api_error = f"JSON parse error: {e}"
        elif item.result.type == "errored":
            ar.api_error = f"Batch error: {item.result.error.type}"
        else:
            ar.api_error = f"Unexpected result type: {item.result.type}"

        results.append(ar)

    return results


# ── report ────────────────────────────────────────────────────────────────────


def _render_question_detail(r: "AssessmentResult") -> list[str]:
    """Return markdown lines for the full per-dimension analysis and thinking of one result."""
    lines: list[str] = []

    if r.analysis:
        lines += ["**Per-dimension analysis:**", ""]
        for dim, text in r.analysis.items():
            lines += [f"**{dim}**", "", text, ""]

    if r.reasoning:
        lines += [
            "<details><summary>Extended thinking (raw)</summary>",
            "",
            r.reasoning,
            "",
            "</details>",
            "",
        ]

    if not r.analysis and not r.reasoning:
        lines += ["_No analysis captured._", ""]

    return lines


def write_report(results: list[AssessmentResult], model: str) -> Path:
    """Write a dated markdown report and return its path."""
    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"llm_assessment_{stamp}.md"

    api_errors = [r for r in results if r.api_error]
    with_issues = [r for r in results if r.has_issues and not r.api_error]
    clean = [r for r in results if not r.has_issues and not r.api_error]
    fixed = [r for r in with_issues if r.fixes and r.fixes.get("changes")]
    unfixed = [r for r in with_issues if not (r.fixes and r.fixes.get("changes"))]

    # Only count errors/warnings from questions that were NOT fixed — fixed issues are resolved
    error_count = sum(1 for r in unfixed for i in r.issues if i.severity == "error")
    warning_count = sum(1 for r in unfixed for i in r.issues if i.severity == "warning")
    result_label = "PASS" if not unfixed and not api_errors else "FAIL"

    lines: list[str] = []

    lines += [
        "# LLM Assessment Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Model:** {model}  ",
        f"**Result:** {result_label}  ",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| Clean — `llm_validated=1` | {len(clean)} |",
        f"| Fixed inline — `llm_validated=1` (report is audit trail) | {len(fixed)} |",
        f"| Needs manual review — `llm_validated=2` | {len(unfixed)} |",
        f"| API failures — `llm_validated=0` (retryable) | {len(api_errors)} |",
        f"| **Total assessed** | **{len(results)}** |",
        "",
        f"Errors: {error_count}  Warnings: {warning_count}",
        "",
    ]

    if clean:
        lines += ["## Clean Questions (llm_validated=1)", ""]
        for r in clean:
            lines += [f"### {r.qid}", ""]
            lines += _render_question_detail(r)

    if fixed:
        lines += ["## Fixed Inline (llm_validated=1)", ""]
        for r in fixed:
            lines += [f"### {r.qid}", ""]
            lines += ["**Issues found:**", ""]
            for issue in r.issues:
                tag = "**ERROR**" if issue.severity == "error" else "**WARNING**"
                lines.append(f"- {tag} `{issue.check}` — {issue.detail}")
            lines.append("")
            lines += ["**Fixes applied:**", ""]
            for change in r.fixes.get("changes", []):
                lines.append(f"- {change}")
            lines.append("")
            lines += _render_question_detail(r)

    if unfixed:
        lines += ["## Needs Manual Review (llm_validated=2)", ""]
        for r in unfixed:
            lines += [f"### {r.qid}", ""]
            lines += ["**Issues flagged (no automatic fix available):**", ""]
            for issue in r.issues:
                tag = "**ERROR**" if issue.severity == "error" else "**WARNING**"
                lines.append(f"- {tag} `{issue.check}` — {issue.detail}")
            lines.append("")
            lines += _render_question_detail(r)

    if api_errors:
        lines += ["## API Failures (llm_validated=0 — will retry on next run)", ""]
        for r in api_errors:
            lines += [f"### {r.qid}", ""]
            lines.append(f"- {r.api_error}")
            lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def print_report(results: list[AssessmentResult], model: str) -> int:
    total = len(results)
    api_errors = [r for r in results if r.api_error]
    with_issues = [r for r in results if r.has_issues and not r.api_error]
    fixed = [r for r in with_issues if r.fixes and r.fixes.get("changes")]
    unfixed = [r for r in with_issues if not (r.fixes and r.fixes.get("changes"))]
    clean = total - len(with_issues) - len(api_errors)

    # Only count errors/warnings from questions that were NOT fixed — fixed issues are resolved
    error_count = sum(1 for r in unfixed for i in r.issues if i.severity == "error")
    warning_count = sum(1 for r in unfixed for i in r.issues if i.severity == "warning")

    print("\n" + "=" * 72)
    print("LLM COGNITIVE ASSESSMENT REPORT")
    print("=" * 72)
    print(f"Model          : {model}")
    print(f"Total assessed : {total}")
    print(f"Clean (tag=1)  : {clean}")
    print(f"Fixed (tag=1)  : {len(fixed)}  (fixed inline, report is audit trail)")
    print(f"Manual (tag=2) : {len(unfixed)}  (needs review)")
    if api_errors:
        print(f"API failures   : {len(api_errors)}  (tag stays 0, retryable)")
    print("=" * 72)

    if api_errors:
        print("\n--- API FAILURES ---\n")
        for r in api_errors:
            print(f"  {r.qid}")
            print(f"    {r.api_error}")
            print()

    if fixed:
        print("\n--- FIXED INLINE ---\n")
        for r in fixed:
            print(f"  {r.qid}")
            for change in r.fixes.get("changes", []):
                print(f"    FIX  {change}")
            print()

    if unfixed:
        print("\n--- NEEDS MANUAL REVIEW ---\n")
        for r in unfixed:
            print(f"  {r.qid}")
            for issue in r.issues:
                tag = "ERROR  " if issue.severity == "error" else "WARNING"
                print(f"    {tag}  [{issue.check}]  {issue.detail}")
            print()

    print("=" * 72)
    print(f"Total errors   : {error_count}")
    print(f"Total warnings : {warning_count}")
    result_label = "PASS" if not unfixed and not api_errors else "FAIL"
    print(f"Result         : {result_label}")
    print("=" * 72 + "\n")

    return len(unfixed) + len(api_errors)


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LLM cognitive assessment of Kubernetes exam questions"
    )
    parser.add_argument("--exam", help="Limit to a specific exam key (e.g. kcsa)")
    parser.add_argument("--limit", type=int, help="Assess only the first N unvalidated questions")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Submit as async batch (50%% cheaper, takes ~1h)",
    )
    parser.add_argument(
        "--poll",
        metavar="BATCH_ID",
        help="Poll an existing batch by ID, write results back to question files, and save report",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("       Export it or prefix the command: ANTHROPIC_API_KEY=sk-... python ...")
        return 1

    client = anthropic.Anthropic(api_key=api_key)

    # ── poll an existing batch ────────────────────────────────────────────────
    if args.poll:
        results = poll_batch(client, args.poll)
        apply_results_to_files(results)
        report_path = write_report(results, args.model)
        failures = print_report(results, args.model)
        print(f"Report saved   : {report_path}")
        print(f"Question files updated with llm_validated tags.\n")
        return 0 if failures == 0 else 1

    # ── load file bank and filter unvalidated ─────────────────────────────────
    bank = load_file_bank(args.exam)
    if not bank:
        print(f"No question files found in {DATA_DIR}" + (f" for exam '{args.exam}'" if args.exam else ""))
        return 1

    questions = get_unvalidated(bank, args.limit)
    if not questions:
        print("No unvalidated questions found (llm_validated == 0). Nothing to do.")
        print("Re-set llm_validated to 0 on any question to re-assess it.")
        return 0

    print(f"Model      : {args.model}")
    print(f"Questions  : {len(questions)} unvalidated (llm_validated=0)")

    # ── batch mode ────────────────────────────────────────────────────────────
    if args.batch:
        print("Submitting batch (async, ~1h) ...")
        batch_id = submit_batch(client, questions, args.model)
        BATCH_ID_FILE.write_text(batch_id)
        print(f"\nBatch submitted: {batch_id}")
        print(f"Saved to       : {BATCH_ID_FILE}")
        print(f"\nPoll results with:")
        print(f"  python tests/llm_assess_questions.py --poll {batch_id}")
        return 0

    # ── sync mode ─────────────────────────────────────────────────────────────
    print("Mode       : sync (use --batch for async / 50% cheaper)\n")
    import time as _time
    start = _time.monotonic()
    results = assess_sync(client, questions, args.model)
    elapsed = _time.monotonic() - start
    print(f"Assessed {len(results)} questions in {elapsed:.1f}s")

    apply_results_to_bank(results, bank)
    save_file_bank(bank)
    report_path = write_report(results, args.model)

    failures = print_report(results, args.model)
    print(f"Report saved   : {report_path}")
    print(f"Question files updated with llm_validated tags.\n")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
