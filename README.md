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
- 40 exam-style multiple choice questions with detailed explanations
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
| Overview of Cloud Native Security | 6 | — |
| Kubernetes Cluster Component Security | 9 | 2 |
| Kubernetes Security Fundamentals | 9 | 4 |
| Kubernetes Threat Model | 6 | — |
| Platform Security | 8 | 4 |
| Compliance and Security Frameworks | 2 | 1 |

## Prerequisites

- Python 3.10+
- `pip install rich`
- For labs: [minikube](https://minikube.sigs.k8s.io/docs/start/) + kubectl

## Roadmap

- [ ] KCNA — Kubernetes and Cloud Native Associate
- [ ] CKA — Certified Kubernetes Administrator
- [ ] CKAD — Certified Kubernetes Application Developer
- [ ] CKS — Certified Kubernetes Security Specialist
