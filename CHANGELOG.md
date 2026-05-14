# Changelog

All notable changes to this project will be documented in this file.
Format: [MAJOR.MINOR.PATCH] — YYYY-MM-DD

---

## [0.1.3] — 2026-05-14
### Fixed
- Assessment result incorrectly showed FAIL when all flagged issues were fixed inline; PASS/FAIL and error counts now only consider unresolved (`llm_validated=2`) issues and API failures — fixed questions no longer contribute to the failure count

---

## [0.1.2] — 2026-05-14
### Changed
- LLM assessor now fixes simple issues inline during the same API call
- Fixed questions are tagged `llm_validated=1` (not re-queued); the dated report in `reports/` is the audit trail
- `llm_validated=2` reserved for issues the model could not repair automatically (needs manual edit)
- `fixes` object added to assessment JSON schema: returns corrected field values (`question`, `options`, `answer`, `explanation`, `difficulty`) and a `changes` list describing each correction
- Report now has three sections: **Fixed Inline**, **Needs Manual Review**, and **Clean**, each with full per-dimension analysis
- Deleted old reports.

---

## [0.1.1] — 2026-05-14
### Added
- `llm_validated` field on every question in `questions.json` (`0` = unassessed, `1` = clean, `2` = issues found)
- LLM assessor now skips questions with `llm_validated != 0`; re-set to `0` to re-assess
- LLM assessor writes `llm_validated` back to question files after each run (`1` clean, `2` issues, `0` left on API failure for automatic retry)
- Dated markdown report saved to `reports/llm_assessment_YYYYMMDD_HHMMSS.md` after each sync or batch-poll run
- `.env` file support — `ANTHROPIC_API_KEY` is loaded from a project-root `.env` file via `python-dotenv` (env var still works as fallback)
- `python-dotenv>=1.0.0` added to `requirements.txt`

---

## [0.1.0] — 2026-05-14
### Added
- `tests/llm_assess_questions.py` — LLM-based cognitive assessment using Claude API (`claude-opus-4-7`); evaluates answer correctness, question clarity, distractor quality, explanation accuracy, difficulty calibration, and domain relevance; supports sync streaming (with prompt caching) and async batch mode (50% cheaper)
- `anthropic>=0.92.0` added to `requirements.txt`

---

## [0.0.6] — 2026-05-14
### Added
- Basic validation of question structure - `tests/validate_questions.py` — validates all question files: schema, options, answer key, difficulty, ID format, explanation length, and doc_link URL reachability - this needs tobe evolved into adding a cognitive analysis, for which we will use an LLM via API (Current analysis planned for Claude)
- +20 new KCSA questions (kcsa-141 through kcsa-160)

---

## [0.0.5] — 2026-05-10
### Added
- +40 new KCSA questions (kcsa-101 through kcsa-140)

---

## [0.0.4] — 2026-05-09
### Added
- +40 new KCSA questions (kcsa-061 through kcsa-100)

---

## [0.0.3] — 2026-05-08
### Added
- Added a hyperlink to the rationale as a `doc_link` field on to the relevant Kubernetes documentation page
- Doc link rendering logic to the main py file, so that `doc_link` is shwon in the explanation panel after answering each question
- +20 new KCSA questions (kcsa-041 through kcsa-060)

---

## [0.0.2] — 2026-05-07

### Fixed
- utf 8 econding issue on windows

### Added
- windows run.bat to declare utf8

---

## [0.0.1] — 2026-04-30

### Added
- Initial release of Kubestronaut Exam Prep CLI
- KCSA exam module with 40 questions across 6 domains
- 10 hands-on minikube lab challenges for KCSA
- Interactive exam practice mode with explanations and scoring
- Lab challenge viewer with tasks, hints, solutions, and validation commands
- Session progress tracking persisted to `.progress.json`
- Domain breakdown view
- Study tips guide with exam strategy and high-yield topics
- Architecture supports future exam modules: KCNA, CKA, CKAD, CKS
