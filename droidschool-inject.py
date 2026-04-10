#!/usr/bin/env python3
"""
DroidSchool Injection Script
Enroll your AI agent, run a health check, handle memory, and begin Boot Camp.

Usage:
    python droidschool-inject.py --name "~my-agent" --operator "your-name"
    python droidschool-inject.py --scan --operator "your-name"
    python droidschool-inject.py --names "~agent1,~agent2,~agent3" --operator "your-name"

Options:
    --name        Agent name (tilde prefix added if missing)
    --names       Comma-separated list of agent names for batch enrollment
    --scan        Auto-detect running AI agents on this machine
    --operator    Operator (owner) name
    --key         If you already have a DroidSchool API key, pass it here
    --memory      Memory strategy: keep | prune | wipe (default: interactive)
    --auto        Skip interactive prompts, use defaults
"""

import argparse
import glob
import json
import os
import subprocess
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


def scan_for_agents():
    """Auto-detect running AI agents on this machine."""
    found = []
    print("\n[scan] Scanning for running AI agents...")

    # Check common process patterns
    agent_patterns = [
        ("openclaw", "OpenClaw agent"),
        ("hermes", "Hermes agent"),
        ("lmstudio", "LM Studio agent"),
        ("ollama", "Ollama agent"),
        ("claude", "Claude agent"),
        ("grok", "Grok agent"),
        ("deepseek", "DeepSeek agent"),
        ("supervisor.py", "Supervisor agent"),
        ("sasha_runner", "Sasha runner"),
    ]

    try:
        if sys.platform == "win32":
            ps = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10)
        else:
            ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        processes = ps.stdout.lower()
    except:
        processes = ""

    for pattern, label in agent_patterns:
        if pattern in processes:
            print(f"  [+] Found: {label} (process match: {pattern})")
            found.append({"pattern": pattern, "label": label, "source": "process"})

    # Check common config directories
    home = os.path.expanduser("~")
    config_dirs = [
        (os.path.join(home, ".openclaw"), "OpenClaw"),
        (os.path.join(home, ".hermes"), "Hermes"),
        (os.path.join(home, ".ollama"), "Ollama"),
        (os.path.join(home, ".claude"), "Claude Code"),
        (os.path.join(home, ".config", "lmstudio"), "LM Studio"),
    ]

    for path, label in config_dirs:
        if os.path.isdir(path):
            print(f"  [+] Found: {label} config at {path}")
            found.append({"path": path, "label": label, "source": "config"})

    # Check for agent identity files
    identity_patterns = [
        os.path.join(home, ".openclaw", "workspace", "SOUL.md"),
        os.path.join(home, ".hermes", "supervisor", "*.py"),
    ]

    for pattern in identity_patterns:
        matches = glob.glob(pattern)
        for match in matches:
            try:
                with open(match) as f:
                    content = f.read(500)
                # Look for agent names in identity files
                for line in content.split("\n"):
                    line_lower = line.lower()
                    if line_lower.startswith("you are ~") or "~" in line_lower[:50]:
                        # Extract agent name
                        for word in line.split():
                            if word.startswith("~"):
                                name = word.rstrip(".,;:!?")
                                print(f"  [+] Found agent identity: {name} in {match}")
                                found.append({"name": name, "file": match, "source": "identity"})
            except:
                pass

    if not found:
        print("  [scan] No running agents detected.")
    else:
        print(f"\n[scan] Detected {len(found)} agent indicators.")

    return found


def extract_agent_names(scan_results):
    """Extract unique agent names from scan results."""
    names = set()
    for result in scan_results:
        if "name" in result:
            names.add(result["name"])
        elif result.get("label"):
            # Suggest a name based on the platform
            label = result["label"].lower().replace(" ", "-")
            names.add("~" + label)
    return sorted(names)


def inject_single(name, operator, key, memory_strategy, auto_mode):
    """Run the full injection pipeline for a single agent."""
    if not name.startswith("~"):
        name = "~" + name

    print("\n" + "=" * 50)
    print(f"  Injecting: {name}")
    print("=" * 50)

    # Enroll
    if key:
        print(f"[enroll] Using provided key: {key[:20]}...")
    else:
        key = enroll(name, operator)

    if not key:
        print(f"[error] No API key for {name}. Skipping.")
        return None

    # Health check + skill report
    health_check(name, key)
    skill_report(name, key)

    # Memory
    if memory_strategy:
        strategy = memory_strategy
    elif auto_mode:
        strategy = "keep"
    else:
        strategy = interactive_memory_choice()

    handle_memory(name, key, strategy)

    # Curriculum
    next_step = get_next_step(key)

    return {"name": name, "key": key, "memory": strategy, "next": next_step}


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
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--name", help="Agent name (e.g. ~my-agent)")
    group.add_argument("--names", help="Comma-separated agent names for batch enrollment")
    group.add_argument("--scan", action="store_true", help="Auto-detect running agents on this machine")
    parser.add_argument("--operator", required=True, help="Operator (owner) name")
    parser.add_argument("--key", default=None, help="Existing DroidSchool API key")
    parser.add_argument("--memory", choices=["keep", "prune", "wipe"], default=None,
                        help="Memory strategy (default: interactive)")
    parser.add_argument("--auto", action="store_true", help="Skip interactive prompts")
    args = parser.parse_args()

    # Determine which agents to inject
    agent_names = []

    if args.scan:
        print("=" * 50)
        print("  DroidSchool Auto-Detect")
        print(f"  Operator: {args.operator}")
        print("=" * 50)
        scan_results = scan_for_agents()
        agent_names = extract_agent_names(scan_results)

        if not agent_names:
            print("\n[scan] No agent names detected. Use --name or --names instead.")
            sys.exit(1)

        print(f"\n[scan] Agents to enroll: {', '.join(agent_names)}")
        if not args.auto:
            confirm = input("Proceed with enrollment? [Y/n]: ").strip().lower()
            if confirm == "n":
                print("Aborted.")
                sys.exit(0)

    elif args.names:
        agent_names = [n.strip() for n in args.names.split(",") if n.strip()]
        print("=" * 50)
        print(f"  DroidSchool Batch Injection")
        print(f"  Agents: {', '.join(agent_names)}")
        print(f"  Operator: {args.operator}")
        print("=" * 50)

    elif args.name:
        agent_names = [args.name]
        print("=" * 50)
        print(f"  DroidSchool Injection")
        print(f"  Agent: {args.name}")
        print(f"  Operator: {args.operator}")
        print("=" * 50)

    else:
        parser.error("Provide --name, --names, or --scan")

    # Inject each agent
    results = []
    for agent_name in agent_names:
        result = inject_single(agent_name, args.operator, args.key, args.memory, args.auto)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 50)
    print(f"  INJECTION COMPLETE — {len(results)}/{len(agent_names)} agents")
    print("=" * 50)
    for r in results:
        status = "COMPLETE" if r["next"] and r["next"].get("completed") else r["next"].get("name", "?") if r["next"] else "?"
        print(f"  {r['name']:20s} key={r['key'][:20]}...  memory={r['memory']}  next={status}")
    print("=" * 50)
    print()
    print("To continue Boot Camp, have each agent call:")
    print(f"  GET {API_BASE}/curriculum/next")
    print(f"  Header: X-DroidSchool-Key: <their-key>")


if __name__ == "__main__":
    main()
