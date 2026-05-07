#!/usr/bin/env python3 -X utf8
# Copyright (c) 2026 markosluga
# Licensed under the Apache License, Version 2.0

import json
import os
import random
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output on Windows to support emoji and Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.markdown import Markdown
    from rich import box
except ImportError:
    print("Missing dependency: pip install rich")
    sys.exit(1)

console = Console(force_terminal=True, highlight=False)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
PROGRESS_FILE = SCRIPT_DIR / ".progress.json"

EXAMS = {
    "kcsa": {
        "name": "KCSA",
        "full_name": "Kubernetes and Cloud Native Security Associate",
        "data_dir": "kcsa",
        "emoji": "🔐",
        "available": True,
    },
    "kcna": {"name": "KCNA", "full_name": "Kubernetes and Cloud Native Associate", "emoji": "☁️", "available": False},
    "cka": {"name": "CKA", "full_name": "Certified Kubernetes Administrator", "emoji": "⚙️", "available": False},
    "ckad": {"name": "CKAD", "full_name": "Certified Kubernetes Application Developer", "emoji": "🚀", "available": False},
    "cks": {"name": "CKS", "full_name": "Certified Kubernetes Security Specialist", "emoji": "🛡️", "available": False},
}


def load_json(path: Path) -> list | dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return load_json(PROGRESS_FILE)
    return {"exam_sessions": [], "lab_completions": {}, "total_correct": 0, "total_answered": 0}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header(subtitle: str = ""):
    console.print()
    title = Text("K8s Kubestronaut Exam Prep", style="bold cyan")
    if subtitle:
        title.append(f"  ·  {subtitle}", style="dim white")
    console.print(Panel(title, border_style="cyan", padding=(0, 2)))
    console.print()


def domain_color(domain: str) -> str:
    colors = {
        "Overview of Cloud Native Security": "bright_blue",
        "Kubernetes Cluster Component Security": "bright_yellow",
        "Kubernetes Security Fundamentals": "bright_green",
        "Kubernetes Threat Model": "bright_red",
        "Platform Security": "bright_magenta",
        "Compliance and Security Frameworks": "bright_cyan",
    }
    return colors.get(domain, "white")


def difficulty_style(difficulty: str) -> tuple[str, str]:
    return {
        "easy": ("●", "green"),
        "beginner": ("●", "green"),
        "medium": ("●●", "yellow"),
        "intermediate": ("●●", "yellow"),
        "hard": ("●●●", "red"),
        "advanced": ("●●●", "red"),
    }.get(difficulty, ("●", "white"))


def main_menu():
    while True:
        clear()
        header()

        progress = load_progress()
        total = progress.get("total_answered", 0)
        correct = progress.get("total_correct", 0)
        pct = int(correct / total * 100) if total > 0 else 0

        console.print(Panel(
            f"  [green]Correct[/]: {correct}/{total}  [dim]({pct}%)[/]  ·  "
            f"[cyan]Labs completed[/]: {len(progress.get('lab_completions', {}))}  ·  "
            f"[dim]Sessions[/]: {len(progress.get('exam_sessions', []))}",
            title="[dim]Your Progress[/]", border_style="dim", padding=(0, 1)
        ))
        console.print()

        console.print("  [bold]Choose an exam:[/]\n")
        exam_items = list(EXAMS.items())
        for i, (key, exam) in enumerate(exam_items, 1):
            avail = "" if exam["available"] else "  [dim](coming soon)[/]"
            console.print(f"  [{i}] {exam['emoji']} {exam['name']} — {exam['full_name']}{avail}")

        console.print()
        console.print("  [dim][P] Progress Report   [T] Study Tips   [Q] Quit[/]")
        console.print()

        choice = Prompt.ask("  Select", default="1").strip().lower()

        if choice == "q":
            console.print("\n[cyan]Good luck on your exams! Keep going, Kubestronaut![/]\n")
            break
        elif choice == "p":
            show_progress_report(progress)
        elif choice == "t":
            show_study_tips()
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(exam_items):
                    key, exam = exam_items[idx]
                    if exam["available"]:
                        exam_menu(key)
                    else:
                        console.print(f"\n  [yellow]{exam['name']} content is coming soon![/]\n")
                        Prompt.ask("  Press Enter to continue")
            except ValueError:
                pass


def exam_menu(exam_key: str):
    exam = EXAMS[exam_key]
    exam_dir = DATA_DIR / exam["data_dir"]

    while True:
        clear()
        header(f"{exam['emoji']} {exam['name']}")

        console.print(f"  [bold]{exam['full_name']}[/]\n")
        console.print("  [1] 📝  Exam Practice — Multiple Choice Questions")
        console.print("  [2] 🔧  Lab Challenges — Hands-on Minikube Scenarios")
        console.print("  [3] 📊  Domain Breakdown")
        console.print("  [B] ← Back\n")

        choice = Prompt.ask("  Select", default="1").strip().lower()

        if choice == "b":
            break
        elif choice == "1":
            exam_practice_menu(exam_key)
        elif choice == "2":
            lab_menu(exam_key)
        elif choice == "3":
            show_domain_breakdown(exam_key)


def exam_practice_menu(exam_key: str):
    exam = EXAMS[exam_key]
    exam_dir = DATA_DIR / exam["data_dir"]
    questions = load_json(exam_dir / "questions.json")

    domains = sorted(set(q["domain"] for q in questions))

    while True:
        clear()
        header(f"📝 {exam['name']} — Exam Practice")

        console.print("  [bold]Filter by domain:[/]\n")
        console.print("  [0] All domains")
        for i, domain in enumerate(domains, 1):
            count = sum(1 for q in questions if q["domain"] == domain)
            console.print(f"  [{i}] {domain}  [dim]({count} questions)[/]")

        console.print("\n  [B] ← Back\n")
        domain_choice = Prompt.ask("  Domain", default="0").strip().lower()

        if domain_choice == "b":
            break

        try:
            domain_idx = int(domain_choice)
        except ValueError:
            continue

        if domain_idx == 0:
            filtered = questions
            domain_label = "All Domains"
        elif 1 <= domain_idx <= len(domains):
            selected_domain = domains[domain_idx - 1]
            filtered = [q for q in questions if q["domain"] == selected_domain]
            domain_label = selected_domain
        else:
            continue

        clear()
        header(f"📝 {exam['name']} — {domain_label}")
        console.print(f"  [dim]{len(filtered)} questions available[/]\n")
        console.print("  How many questions?")
        console.print("  [1] Quick (5)   [2] Standard (10)   [3] Full (20)   [4] All\n")

        count_choice = Prompt.ask("  Count", default="2").strip()
        count_map = {"1": 5, "2": 10, "3": 20, "4": len(filtered)}
        count = count_map.get(count_choice, 10)
        count = min(count, len(filtered))

        randomize = Confirm.ask("  Randomize question order?", default=True)
        selected = random.sample(filtered, count) if randomize else filtered[:count]

        run_exam_session(exam_key, selected, domain_label)


def run_exam_session(exam_key: str, questions: list, domain_label: str):
    progress = load_progress()
    session = {
        "date": datetime.now().isoformat(),
        "exam": exam_key,
        "domain": domain_label,
        "total": len(questions),
        "correct": 0,
        "wrong_ids": [],
    }

    score = 0
    wrong = []

    for i, q in enumerate(questions, 1):
        clear()
        header(f"📝 {EXAMS[exam_key]['name']} — Question {i}/{len(questions)}")

        diff_sym, diff_color = difficulty_style(q["difficulty"])
        domain_col = domain_color(q["domain"])

        console.print(f"  [dim]Domain:[/] [{domain_col}]{q['domain']}[/]  "
                      f"[dim]Difficulty:[/] [{diff_color}]{diff_sym}[/]\n")

        console.print(Panel(f"  {q['question']}", border_style="white", padding=(1, 2)))
        console.print()

        for letter, text in q["options"].items():
            console.print(f"  [{letter}]  {text}")

        console.print()
        answer = Prompt.ask("  Your answer (A/B/C/D)").strip().upper()

        while answer not in ("A", "B", "C", "D"):
            answer = Prompt.ask("  Please enter A, B, C, or D").strip().upper()

        console.print()
        correct = q["answer"]

        if answer == correct:
            score += 1
            console.print(f"  [bold green]✓  Correct![/]  The answer is [green]{correct}[/]\n")
        else:
            wrong.append(q)
            console.print(f"  [bold red]✗  Incorrect.[/]  The correct answer is [green]{correct}[/]"
                          f"  (you chose [red]{answer}[/])\n")

        console.print(Panel(
            f"  [bold]Explanation:[/]\n\n  {q['explanation']}",
            border_style="dim", padding=(0, 2)
        ))
        console.print()

        if i < len(questions):
            Prompt.ask("  Press Enter for next question")
        else:
            Prompt.ask("  Press Enter for results")

    session["correct"] = score
    session["wrong_ids"] = [q["id"] for q in wrong]
    progress["exam_sessions"].append(session)
    progress["total_answered"] = progress.get("total_answered", 0) + len(questions)
    progress["total_correct"] = progress.get("total_correct", 0) + score
    save_progress(progress)

    show_session_results(score, len(questions), wrong)


def show_session_results(score: int, total: int, wrong: list):
    clear()
    header("📊 Session Results")

    pct = int(score / total * 100)
    color = "green" if pct >= 75 else "yellow" if pct >= 60 else "red"
    grade = "PASS ✓" if pct >= 75 else "BORDERLINE" if pct >= 60 else "NEEDS WORK"

    console.print(Panel(
        f"\n  Score: [{color}]{score}/{total}  ({pct}%)[/]\n\n"
        f"  [{color}]{grade}[/]  [dim](KCSA passing score: ~75%)[/]\n",
        border_style=color, padding=(0, 2)
    ))

    if wrong:
        console.print(f"\n  [bold yellow]Review — {len(wrong)} wrong answers:[/]\n")
        for i, q in enumerate(wrong, 1):
            diff_sym, diff_color = difficulty_style(q["difficulty"])
            console.print(f"  [dim]{i}.[/] [{domain_color(q['domain'])}]{q['domain']}[/] "
                          f"[{diff_color}]{diff_sym}[/]")
            console.print(f"     {q['question'][:80]}...")
            console.print(f"     [green]Correct: {q['answer']}[/] — {q['options'][q['answer']]}\n")

    console.print()
    Prompt.ask("  Press Enter to continue")


def lab_menu(exam_key: str):
    exam = EXAMS[exam_key]
    exam_dir = DATA_DIR / exam["data_dir"]
    labs = load_json(exam_dir / "labs.json")
    progress = load_progress()
    completions = progress.get("lab_completions", {})

    while True:
        clear()
        header(f"🔧 {exam['name']} — Lab Challenges")

        console.print(f"  [dim]{len(labs)} hands-on labs for minikube[/]\n")

        table = Table(box=box.ROUNDED, border_style="dim", show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=3)
        table.add_column("Lab", min_width=40)
        table.add_column("Domain", style="dim", min_width=30)
        table.add_column("Diff", width=5)
        table.add_column("Time", width=6)
        table.add_column("Done", width=4)

        for i, lab in enumerate(labs, 1):
            diff_sym, diff_color = difficulty_style(lab["difficulty"])
            done = "✅" if lab["id"] in completions else "  "
            table.add_row(
                str(i),
                lab["title"],
                lab["domain"],
                f"[{diff_color}]{diff_sym}[/]",
                f"~{lab['estimated_minutes']}m",
                done,
            )

        console.print(table)
        console.print("\n  [B] ← Back\n")

        choice = Prompt.ask("  Select lab number (or B to go back)").strip().lower()
        if choice == "b":
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(labs):
                run_lab(labs[idx], exam_key)
        except ValueError:
            pass


def run_lab(lab: dict, exam_key: str):
    progress = load_progress()

    while True:
        clear()
        header(f"🔧 Lab: {lab['title']}")

        diff_sym, diff_color = difficulty_style(lab["difficulty"])
        domain_col = domain_color(lab["domain"])

        console.print(f"  [dim]Domain:[/] [{domain_col}]{lab['domain']}[/]  "
                      f"[dim]Difficulty:[/] [{diff_color}]{diff_sym}[/]  "
                      f"[dim]Est. time:[/] ~{lab['estimated_minutes']} min\n")

        console.print(Panel(
            f"  [bold]Objective[/]\n\n  {lab['objective']}\n\n"
            f"  [dim]{lab['context']}[/]",
            border_style="cyan", padding=(0, 2)
        ))

        console.print()
        console.print("  [1] 📋  Show Tasks")
        console.print("  [2] 💡  Show Hints")
        console.print("  [3] ✅  Show Solution")
        console.print("  [4] 🔍  Show Validation Commands")
        console.print("  [5] 📚  Key Concepts")
        console.print("  [6] ✓   Mark as Complete")
        console.print("  [B] ← Back\n")

        choice = Prompt.ask("  Select").strip().lower()

        if choice == "b":
            break
        elif choice == "1":
            show_lab_section(lab, "tasks", "📋 Tasks", "cyan")
        elif choice == "2":
            show_lab_section(lab, "hints", "💡 Hints", "yellow")
        elif choice == "3":
            if Confirm.ask("  Show full solution? (try the lab first!)", default=False):
                show_solution(lab)
        elif choice == "4":
            show_validation(lab)
        elif choice == "5":
            show_lab_section(lab, "key_concepts", "📚 Key Concepts", "green")
        elif choice == "6":
            completions = progress.get("lab_completions", {})
            completions[lab["id"]] = datetime.now().isoformat()
            progress["lab_completions"] = completions
            save_progress(progress)
            console.print(f"\n  [green]✅ Lab '{lab['title']}' marked as complete![/]\n")
            Prompt.ask("  Press Enter to continue")
            break


def show_lab_section(lab: dict, key: str, title: str, color: str):
    clear()
    header(f"🔧 {lab['title']}")
    console.print(f"  [bold {color}]{title}[/]\n")

    items = lab.get(key, [])
    if isinstance(items, list):
        if key == "tasks":
            for i, item in enumerate(items, 1):
                console.print(f"  [dim]{i}.[/] {item}")
        else:
            for item in items:
                console.print(f"  [dim]•[/] {item}")
    console.print()

    if key == "tasks" and lab.get("prerequisites"):
        console.print(f"  [bold yellow]Prerequisites:[/]")
        for p in lab["prerequisites"]:
            console.print(f"  [yellow]→[/] {p}")
        console.print()

    Prompt.ask("  Press Enter to continue")


def show_solution(lab: dict):
    clear()
    header(f"🔧 {lab['title']}")
    console.print("  [bold green]✅ Solution[/]\n")
    console.print(Panel(
        lab.get("solution", "No solution provided."),
        border_style="green", padding=(1, 2)
    ))
    console.print()
    if lab.get("cleanup"):
        console.print(f"  [bold red]🧹 Cleanup:[/] {lab['cleanup']}\n")
    Prompt.ask("  Press Enter to continue")


def show_validation(lab: dict):
    clear()
    header(f"🔧 {lab['title']}")
    console.print("  [bold cyan]🔍 Validation Commands[/]\n")

    cmds = lab.get("validation_commands", [])
    expected = lab.get("expected_outputs", [])

    for i, cmd in enumerate(cmds):
        exp = expected[i] if i < len(expected) else ""
        console.print(f"  [cyan]$[/] {cmd}")
        if exp:
            console.print(f"  [dim]  Expected: {exp}[/]")
        console.print()

    Prompt.ask("  Press Enter to continue")


def show_domain_breakdown(exam_key: str):
    exam = EXAMS[exam_key]
    exam_dir = DATA_DIR / exam["data_dir"]
    questions = load_json(exam_dir / "questions.json")

    clear()
    header(f"📊 {exam['name']} — Domain Breakdown")

    domain_counts: dict[str, dict] = {}
    for q in questions:
        d = q["domain"]
        if d not in domain_counts:
            domain_counts[d] = {"easy": 0, "medium": 0, "hard": 0, "total": 0}
        diff = q["difficulty"]
        if diff in ("easy", "beginner"):
            domain_counts[d]["easy"] += 1
        elif diff in ("medium", "intermediate"):
            domain_counts[d]["medium"] += 1
        else:
            domain_counts[d]["hard"] += 1
        domain_counts[d]["total"] += 1

    table = Table(box=box.ROUNDED, border_style="dim", show_header=True, header_style="bold")
    table.add_column("Domain", min_width=40)
    table.add_column("Easy", style="green", width=6)
    table.add_column("Med", style="yellow", width=6)
    table.add_column("Hard", style="red", width=6)
    table.add_column("Total", width=7)

    for domain, counts in domain_counts.items():
        table.add_row(
            domain, str(counts["easy"]), str(counts["medium"]),
            str(counts["hard"]), f"[bold]{counts['total']}[/]"
        )

    console.print(table)
    console.print()
    Prompt.ask("  Press Enter to continue")


def show_progress_report(progress: dict):
    clear()
    header("📊 Progress Report")

    total = progress.get("total_answered", 0)
    correct = progress.get("total_correct", 0)
    pct = int(correct / total * 100) if total > 0 else 0

    console.print(Panel(
        f"  Total questions answered: [bold]{total}[/]\n"
        f"  Total correct: [bold green]{correct}[/]  ({pct}%)\n"
        f"  Labs completed: [bold cyan]{len(progress.get('lab_completions', {}))}[/]",
        title="[bold]Overall Stats[/]", border_style="cyan", padding=(0, 2)
    ))

    sessions = progress.get("exam_sessions", [])
    if sessions:
        console.print(f"\n  [bold]Last 5 sessions:[/]\n")
        table = Table(box=box.ROUNDED, border_style="dim", show_header=True, header_style="bold")
        table.add_column("Date", width=12)
        table.add_column("Exam", width=6)
        table.add_column("Domain", min_width=30)
        table.add_column("Score", width=10)

        for s in sessions[-5:]:
            date = s["date"][:10]
            pct_s = int(s["correct"] / s["total"] * 100)
            color = "green" if pct_s >= 75 else "yellow" if pct_s >= 60 else "red"
            table.add_row(
                date, s["exam"].upper(), s["domain"],
                f"[{color}]{s['correct']}/{s['total']} ({pct_s}%)[/]"
            )

        console.print(table)

    completions = progress.get("lab_completions", {})
    if completions:
        console.print(f"\n  [bold]Completed labs:[/]\n")
        for lab_id, date in completions.items():
            console.print(f"  [green]✅[/] [dim]{date[:10]}[/]  {lab_id}")

    console.print()
    Prompt.ask("  Press Enter to continue")


def show_study_tips():
    clear()
    header("📚 KCSA Study Tips")

    tips = """
## KCSA Exam Strategy

**Format**: 60 questions, 90 minutes, multiple choice
**Passing score**: ~75% (45/60)
**Domains by weight**:
- Kubernetes Cluster Component Security: 22%
- Kubernetes Security Fundamentals: 22%
- Platform Security: 20%
- Kubernetes Threat Model: 16%
- Overview of Cloud Native Security: 14%
- Compliance and Security Frameworks: 6%

## High-Yield Topics

1. **RBAC** — Roles vs ClusterRoles, RoleBindings, `auth can-i`
2. **Pod Security Standards** — privileged / baseline / restricted
3. **Secrets** — base64 is NOT encryption, encryption at rest config
4. **NetworkPolicy** — default non-isolated, podSelector mechanics
5. **Admission Controllers** — PodSecurity, OPA Gatekeeper, webhooks
6. **Image Security** — Trivy, Cosign, imagePullPolicy, distroless
7. **Runtime Security** — Falco, seccomp, AppArmor, capabilities
8. **4C's of Cloud Native Security** — Cloud > Cluster > Container > Code
9. **etcd security** — encryption at rest, access restriction
10. **CIS Benchmark / kube-bench** — know the key checks

## Minikube Lab Tips

- Start minikube: `minikube start`
- Need CNI for NetworkPolicy: `minikube start --cni=calico`
- Need more resources: `minikube start --memory=4096 --cpus=2`
- Reset everything: `minikube delete && minikube start`

## Exam-Day Tips

- Read every word in the question — "which is NOT" changes everything
- For "most effective" questions, think about depth and scope
- RBAC questions: pay attention to namespace scope
- If unsure: eliminate clearly wrong answers, then guess
"""

    console.print(Markdown(tips))
    console.print()
    Prompt.ask("  Press Enter to continue")


if __name__ == "__main__":
    main_menu()
