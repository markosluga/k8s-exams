# Technical Documentation — Kubestronaut Exam Prep

## Architecture

Single-file Python CLI (`k8s_exam_prep.py`) with JSON data files. No database, no server — runs entirely offline.

```
k8s-exams/
├── k8s_exam_prep.py      # Main application
├── requirements.txt       # Python dependencies
├── .env                   # API keys — gitignored, not committed
├── data/
│   └── kcsa/
│       ├── questions.json # Exam questions (array of question objects)
│       └── labs.json      # Lab challenges (array of lab objects)
├── tests/
│   ├── validate_questions.py    # Structural validator
│   └── llm_assess_questions.py  # LLM cognitive assessor
├── reports/               # Generated assessment reports — gitignored
├── .progress.json         # Auto-created; tracks session history (gitignored)
└── docs/technical.md      # This file
```

## Data Schemas

### Question Object (`questions.json`)

```json
{
  "id": "kcsa-001",
  "domain": "Overview of Cloud Native Security",
  "difficulty": "easy | medium | hard",
  "question": "Question text",
  "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
  "answer": "A",
  "explanation": "Why this is correct and why the others are not.",
  "doc_link": "https://kubernetes.io/docs/...",
  "llm_validated": 0
}
```

`llm_validated` is managed exclusively by `tests/llm_assess_questions.py` and is invisible to the exam simulator:

| Value | Meaning |
|-------|---------|
| `0` | Not yet assessed — will be processed on next assessor run |
| `1` | Clean (no issues found) **or** issues found and fixed inline during assessment |
| `2` | Issues found that could not be repaired automatically — needs manual edit |

Re-set to `0` on any question to trigger re-assessment. Dated reports in `reports/` are the audit trail for all automatic fixes applied.

### Lab Object (`labs.json`)

```json
{
  "id": "kcsa-lab-001",
  "title": "Short descriptive title",
  "domain": "Domain name",
  "difficulty": "beginner | intermediate | advanced",
  "estimated_minutes": 20,
  "objective": "What the user will build and learn",
  "context": "Why this matters for the exam",
  "prerequisites": ["minikube start"],
  "tasks": ["Step 1", "Step 2", "..."],
  "hints": ["Hint 1", "Hint 2"],
  "solution": "Full solution commands/YAML",
  "validation_commands": ["kubectl ..."],
  "expected_outputs": ["expected result"],
  "cleanup": "kubectl delete ...",
  "key_concepts": ["Concept 1", "Concept 2"]
}
```

## Progress Tracking

Progress is stored in `.progress.json` (auto-created, gitignored):

```json
{
  "exam_sessions": [
    {
      "date": "2026-04-30T10:00:00",
      "exam": "kcsa",
      "domain": "All Domains",
      "total": 10,
      "correct": 8,
      "wrong_ids": ["kcsa-007", "kcsa-019"]
    }
  ],
  "lab_completions": {
    "kcsa-lab-001": "2026-04-30T11:00:00"
  },
  "total_correct": 8,
  "total_answered": 10
}
```

## Adding a New Exam

1. Add an entry to the `EXAMS` dict in `k8s_exam_prep.py` with `"available": True`
2. Create `data/<exam_key>/questions.json` following the question schema
3. Create `data/<exam_key>/labs.json` following the lab schema
4. No other code changes needed — the menus auto-populate from the EXAMS dict

## Validation / Testing

### Structural Validator

Run before committing new question files:

```
python tests/validate_questions.py
```

Scans every `data/<exam>/questions.json` and checks:

| Check | Severity | Details |
|---|---|---|
| Schema | ERROR | All required fields present with correct types |
| Options | ERROR | Exactly keys A, B, C, D; values non-empty strings |
| Answer | ERROR | Answer key exists in options |
| Difficulty | ERROR | One of `easy`, `medium`, `hard` |
| ID format | ERROR | Matches `<exam>-NNN` (e.g. `kcsa-042`) |
| Duplicate IDs | ERROR | Unique across all exam files |
| Explanation length | WARNING | At least 50 characters |
| doc_link reachability | ERROR/WARNING | HTTP GET returns 200 |

Exit code 0 = all questions pass (no errors). Exit code 1 = at least one error.

### LLM Cognitive Assessor

Run on demand to assess semantic quality using the Claude API.

**Setup** — create a `.env` file in the project root (gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
```

```
pip install anthropic python-dotenv

# Sync mode — stream results one by one with prompt caching
python tests/llm_assess_questions.py

# Async batch mode — 50% cheaper, results in ~1 hour
python tests/llm_assess_questions.py --batch
python tests/llm_assess_questions.py --poll <BATCH_ID>

# Scope to a specific exam or sample
python tests/llm_assess_questions.py --exam kcsa --limit 20

# Use a cheaper model for faster/lower-cost checks
python tests/llm_assess_questions.py --model claude-haiku-4-5
```

The assessor only processes questions with `llm_validated == 0`. In a single API call it evaluates and — where possible — repairs each question. After each run it writes corrected fields and tags back to `questions.json` and saves a dated report to `reports/llm_assessment_YYYYMMDD_HHMMSS.md`.

**Assessment → fix → tag flow:**

| Outcome | Tag set | Action taken |
|---------|---------|--------------|
| No issues found | `1` | Question marked clean |
| Issues found, fix returned | `1` | Corrected fields written to `questions.json`; report records what changed |
| Issues found, no fix possible | `2` | Question flagged for manual edit |
| API error | `0` | Question left unchanged; retried automatically on next run |

Questions tagged `2` require a human to open `questions.json`, correct the flagged field, and reset `llm_validated` to `0` for re-assessment. The corresponding report entry describes exactly what needs fixing.

Each question is sent to `claude-opus-4-7` (default) with adaptive thinking enabled. The model evaluates:

| Check | Severity | What is assessed |
|---|---|---|
| answer_correctness | ERROR | Is the stated answer definitively best per Kubernetes docs? |
| question_clarity | WARNING | Is the question unambiguous and grammatically clear? |
| distractor_quality | WARNING | Are wrong answers plausible but clearly incorrect to an expert? |
| explanation_accuracy | ERROR | Is the explanation factually correct? |
| difficulty_calibration | WARNING | Is easy/medium/hard rating appropriate? |
| domain_relevance | WARNING | Does the question actually test the stated domain? |

The system prompt is cached (prompt caching) so the per-question cost is low after the first call. Batch mode submits all questions in one API call at 50% of standard pricing.

## Dependencies

- **rich** ≥ 13.0: Terminal UI (panels, tables, markdown rendering, prompts)
- **anthropic** ≥ 0.92.0: Claude API client (LLM assessor only)
- **python-dotenv** ≥ 1.0.0: `.env` file loading for `ANTHROPIC_API_KEY` (LLM assessor only)
- Python stdlib only otherwise: `json`, `os`, `random`, `sys`, `pathlib`, `datetime`

## Key Design Decisions

- **JSON data files** — easy to edit and extend without touching Python code
- **Offline-first** — all content embedded, no network calls
- **No framework** — single script, no setup beyond `pip install rich`
- **Progress file excluded from git** — `.progress.json` must be in `.gitignore`
