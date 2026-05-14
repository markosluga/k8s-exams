# Technical Documentation — Kubestronaut Exam Prep

## Architecture

Single-file Python CLI (`k8s_exam_prep.py`) with JSON data files. No database, no server — runs entirely offline.

```
k8s-exams/
├── k8s_exam_prep.py      # Main application
├── requirements.txt       # Python dependencies (rich only)
├── data/
│   └── kcsa/
│       ├── questions.json # Exam questions (array of question objects)
│       └── labs.json      # Lab challenges (array of lab objects)
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
  "explanation": "Why this is correct and why the others are not."
}
```

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

Run the question validator before committing new question files:

```
python tests/validate_questions.py
```

The script scans every `data/<exam>/questions.json` and checks:

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

## Dependencies

- **rich** ≥ 13.0: Terminal UI (panels, tables, markdown rendering, prompts)
- Python stdlib only otherwise: `json`, `os`, `random`, `sys`, `pathlib`, `datetime`

## Key Design Decisions

- **JSON data files** — easy to edit and extend without touching Python code
- **Offline-first** — all content embedded, no network calls
- **No framework** — single script, no setup beyond `pip install rich`
- **Progress file excluded from git** — `.progress.json` must be in `.gitignore`
