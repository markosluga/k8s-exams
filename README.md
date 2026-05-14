# ⎈ Kubestronaut Exam Prep

A terminal-based study tool for the five Kubestronaut certification exams. Currently includes full content for **KCSA** (Kubernetes and Cloud Native Security Associate).

## Quick Start

Linux/Mac

```bash
pip install rich
python k8s_exam_prep.py
```
For Windows please use the run file, to set the encoding to utf-8

```bash
pip install rich
run.bat
```

## What's Inside

**KCSA — Kubernetes and Cloud Native Security Associate**
- 160 exam-style multiple choice questions with detailed explanations and documentation links
- 10 hands-on minikube lab challenges
- Progress tracking across sessions

## Two Study Modes

### 📝 Exam Practice
Multiple choice questions organized by domain. Choose 5, 10, 20, or all questions. After each answer you see an explanation of why it's right or wrong. Session scores are saved.

### 🔧 Lab Challenges
Hands-on scenarios you build on a local minikube cluster. Each lab includes:
- Objective and context
- Step-by-step tasks
- Progressive hints (try before you peek)
- Full solution
- Validation commands to verify your work
- Key concepts summary

## KCSA Domains Covered

| Domain | Questions | Labs |
|--------|-----------|------|
| Overview of Cloud Native Security | 23 | — |
| Kubernetes Cluster Component Security | 34 | 2 |
| Kubernetes Security Fundamentals | 29 | 4 |
| Kubernetes Threat Model | 29 | — |
| Platform Security | 28 | 4 |
| Compliance and Security Frameworks | 17 | 1 |
| **Total** | **160** | **11** |

## Prerequisites

- Python 3.10+
- `pip install rich`
- For labs: [minikube](https://minikube.sigs.k8s.io/docs/start/) + kubectl

## Roadmap

- [ ] KCNA — Kubernetes and Cloud Native Associate
- [ ] CKA — Certified Kubernetes Administrator
- [ ] CKAD — Certified Kubernetes Application Developer
- [ ] CKS — Certified Kubernetes Security Specialist
