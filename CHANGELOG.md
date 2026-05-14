# Changelog

All notable changes to this project will be documented in this file.
Format: [MAJOR.MINOR.PATCH] — YYYY-MM-DD

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
