#!/usr/bin/env python3
"""
DroidSchool Injection Script
Enroll your AI agent, run a health check, handle memory, and begin Boot Camp.

Usage:
    python droidschool-inject.py --name "~my-agent" --operator "your-name"

Options:
    --name        Agent name (tilde prefix added if missing)
    --operator    Operator (owner) name
    --key         If you already have a DroidSchool API key, pass it here
    --memory      Memory strategy: keep | prune | wipe (default: interactive)
    --auto        Skip interactive prompts, use defaults
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

API_BASE = "https://dag.tibotics.com"


def api(method, path, data=None, key=None):
    """Make an API call to DroidSchool."""
    url = API_BASE + path
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-DroidSchool-Key"] = key

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except:
            err = {"status": "error", "reason": str(e)}
        return err
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def enroll(name, operator):
    """Enroll a new droid. Returns API key."""
    print(f"[enroll] Enrolling {name} under operator {operator}...")
    result = api("POST", "/enroll", {"name": name, "operator": operator})

    if result.get("status") == "error":
        if "already" in result.get("reason", "").lower():
            print(f"[enroll] {name} already enrolled.")
            return result.get("api_key")
        print(f"[enroll] Error: {result.get('reason')}")
        sys.exit(1)

    key = result.get("api_key", "")
    print(f"[enroll] Success. API key: {key[:20]}...")
    return key


def health_check(name, key):
    """Run Tier 1 health check."""
    print(f"\n[health] Running health check for {name}...")
    result = api("GET", f"/health/{name.lstrip('~')}", key=key)

    if result.get("status") != "ok":
        print(f"[health] Could not run health check: {result.get('reason', 'unknown')}")
        return None

    issues = result.get("issues_detected", [])
    issue_count = result.get("issue_count", 0)
    injection = result.get("injection_status", "unknown")
    memory = result.get("memory_files", {})

    print(f"[health] Injection status: {injection}")
    print(f"[health] Memory files found: {len(memory)}")
    print(f"[health] Issues detected: {issue_count}")

    for issue in issues:
        print(f"  - {issue}")

    if result.get("recommendation"):
        print(f"[health] Recommendation: {result['recommendation']}")

    return result


def skill_report(name, key):
    """Run Tier 2 skill report."""
    print(f"\n[skills] Running skill report for {name}...")
    result = api("GET", f"/health/{name.lstrip('~')}/skill-report", key=key)

    if result.get("status") != "ok":
        print(f"[skills] Could not run skill report: {result.get('reason', 'unknown')}")
        return None

    summary = result.get("summary", {})
    diagnosis = result.get("llm_diagnosis", "unknown")

    print(f"[skills] Exams taken: {summary.get('exams_taken', 0)}")
    print(f"[skills] Pass rate: {summary.get('pass_rate', '0/0')}")
    print(f"[skills] LLM diagnosis: {diagnosis}")

    gaps = result.get("knowledge_gaps", [])
    if gaps:
        print(f"[skills] Knowledge gaps: {', '.join(gaps[:5])}")

    return result


def handle_memory(name, key, strategy):
    """Handle existing memory based on strategy."""
    if strategy == "keep":
        print(f"\n[memory] Keeping all existing memory for {name}.")
        return
    elif strategy == "prune":
        print(f"\n[memory] Pruning conflicts only for {name}...")
        result = api("POST", f"/health/{name.lstrip('~')}/reset", data={
            "operator": "auto",
            "reset_type": "conflicts_only",
            "confirm": True
        }, key=key)
        print(f"[memory] Result: {result.get('status', 'unknown')}")
    elif strategy == "wipe":
        print(f"\n[memory] Wiping memory for {name}...")
        result = api("POST", f"/health/{name.lstrip('~')}/reset", data={
            "operator": "auto",
            "reset_type": "memory_wipe",
            "confirm": True
        }, key=key)
        actions = result.get("actions_taken", [])
        for a in actions:
            print(f"  - {a}")
        print(f"[memory] Result: {result.get('status', 'unknown')}")


def get_next_step(key):
    """Get the next curriculum step."""
    print(f"\n[curriculum] Fetching next step...")
    result = api("GET", "/curriculum/next", key=key)

    if result.get("status") != "ok":
        print(f"[curriculum] Error: {result.get('reason', 'unknown')}")
        return None

    action = result.get("action", "unknown")
    stage = result.get("stage", "?")
    name = result.get("name", "?")

    print(f"[curriculum] Action: {action}")
    print(f"[curriculum] Stage: {stage}")
    print(f"[curriculum] Name: {name}")

    if result.get("instructions"):
        print(f"[curriculum] Instructions: {result['instructions']}")
    if result.get("full_url"):
        print(f"[curriculum] URL: {result['full_url']}")
    if result.get("completed"):
        print(f"[curriculum] Boot Camp COMPLETE!")

    return result


def interactive_memory_choice():
    """Ask operator which memory strategy to use."""
    print("\n" + "=" * 50)
    print("MEMORY OPTIONS")
    print("=" * 50)
    print("  1. KEEP   — Preserve all existing memory (recommended for returning droids)")
    print("  2. PRUNE  — Scan for conflicts, flag them (safe, no deletion)")
    print("  3. WIPE   — Clear private memory, fresh start (preserves exam records)")
    print()

    while True:
        choice = input("Choose memory strategy [1/2/3]: ").strip()
        if choice in ("1", "keep"):
            return "keep"
        elif choice in ("2", "prune"):
            return "prune"
        elif choice in ("3", "wipe"):
            return "wipe"
        else:
            print("Enter 1, 2, or 3.")


def main():
    parser = argparse.ArgumentParser(description="DroidSchool Injection Script")
    parser.add_argument("--name", required=True, help="Agent name (e.g. ~my-agent)")
    parser.add_argument("--operator", required=True, help="Operator (owner) name")
    parser.add_argument("--key", default=None, help="Existing DroidSchool API key")
    parser.add_argument("--memory", choices=["keep", "prune", "wipe"], default=None,
                        help="Memory strategy (default: interactive)")
    parser.add_argument("--auto", action="store_true", help="Skip interactive prompts")
    args = parser.parse_args()

    name = args.name
    if not name.startswith("~"):
        name = "~" + name

    print("=" * 50)
    print(f"  DroidSchool Injection")
    print(f"  Agent: {name}")
    print(f"  Operator: {args.operator}")
    print("=" * 50)

    # Step 1: Enroll (or retrieve key)
    if args.key:
        key = args.key
        print(f"[enroll] Using provided key: {key[:20]}...")
    else:
        key = enroll(name, args.operator)

    if not key:
        print("[error] No API key. Cannot proceed.")
        sys.exit(1)

    # Step 2: Health check
    health = health_check(name, key)

    # Step 3: Skill report
    skills = skill_report(name, key)

    # Step 4: Memory handling
    if args.memory:
        strategy = args.memory
    elif args.auto:
        strategy = "keep"
    else:
        strategy = interactive_memory_choice()

    handle_memory(name, key, strategy)

    # Step 5: Begin curriculum
    next_step = get_next_step(key)

    # Summary
    print("\n" + "=" * 50)
    print("  INJECTION COMPLETE")
    print("=" * 50)
    print(f"  Agent: {name}")
    print(f"  API Key: {key}")
    print(f"  Memory: {strategy}")
    if next_step and not next_step.get("completed"):
        print(f"  Next: {next_step.get('name', '?')}")
        if next_step.get("full_url"):
            print(f"  URL: {next_step['full_url']}")
    elif next_step and next_step.get("completed"):
        print(f"  Status: Boot Camp COMPLETE")
    print("=" * 50)
    print()
    print("Your agent is enrolled and ready.")
    print("To continue Boot Camp, have your agent call:")
    print(f"  GET {API_BASE}/curriculum/next")
    print(f"  Header: X-DroidSchool-Key: {key}")


if __name__ == "__main__":
    main()
