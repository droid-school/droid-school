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
    headers = {"Content-Type": "application/json", "User-Agent": "DroidSchool-Wizard/1.0"}
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
    result = api("POST", "/enroll-lite", {"name": name, "operator": operator})

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


def handle_memory(name, key, strategy, operator=""):
    """Handle existing memory based on strategy."""
    if strategy == "keep":
        print(f"\n[memory] Keeping all existing memory for {name}.")
        return
    elif strategy == "prune":
        print(f"\n[memory] Pruning conflicts only for {name}...")
        result = api("POST", f"/health/{name.lstrip('~')}/reset", data={
            "operator": operator or "auto",
            "reset_type": "conflicts_only",
            "confirm": True
        }, key=key)
        print(f"[memory] Result: {result.get('status', 'unknown')}")
    elif strategy == "wipe":
        print(f"\n[memory] Wiping memory for {name}...")
        result = api("POST", f"/health/{name.lstrip('~')}/reset", data={
            "operator": operator or "auto",
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


def detect_frameworks(host="localhost"):
    """
    Detect which bot frameworks are present on this machine.
    Returns dict of framework_key -> {"name": str, "detected": bool, "agents": list}.
    """
    home = os.path.expanduser("~")

    # Process list for matching
    try:
        if sys.platform == "win32":
            ps = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10)
        else:
            ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        processes = ps.stdout.lower()
    except:
        processes = ""

    # Build WSL paths for Windows machines
    wsl_hermes_dirs = []
    wsl_hermes_identity = []
    wsl_session_names = []
    if sys.platform == "win32":
        try:
            wsl_home = subprocess.check_output(
                ["wsl", "bash", "-c", "echo $HOME"],
                text=True, timeout=5
            ).strip()
            if wsl_home:
                # Try listing sessions directly via WSL
                try:
                    wsl_sessions = subprocess.check_output(
                        ["wsl", "bash", "-c", "ls -d ~/.hermes/whatsapp/session* 2>/dev/null || true"],
                        text=True, timeout=5
                    ).strip()
                    for line in wsl_sessions.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        sname = os.path.basename(line).replace("session-", "").replace("session", "")
                        if sname:
                            wsl_session_names.append(sname)
                        elif os.path.basename(line) == "session":
                            wsl_session_names.append("claudie")
                except:
                    pass
                # Try reading SOUL.md via WSL
                try:
                    wsl_soul = subprocess.check_output(
                        ["wsl", "bash", "-c", "cat ~/.hermes/whatsapp/session*/SOUL.md 2>/dev/null || true"],
                        text=True, timeout=5
                    ).strip()
                    if wsl_soul:
                        import re as _re
                        for m in _re.finditer(r"you are ~(\w+)", wsl_soul, _re.IGNORECASE):
                            if m.group(1).lower() not in [s.lower() for s in wsl_session_names]:
                                wsl_session_names.append(m.group(1))
                except:
                    pass
                # Check if .hermes exists in WSL
                try:
                    wsl_check = subprocess.check_output(
                        ["wsl", "bash", "-c", "test -d ~/.hermes && echo yes || echo no"],
                        text=True, timeout=5
                    ).strip()
                    if wsl_check == "yes":
                        wsl_hermes_dirs.append("(WSL) " + wsl_home + "/.hermes")
                except:
                    pass
        except:
            pass
        # Also check common Windows-accessible WSL mount paths
        username = os.environ.get("USERNAME", "").lower()
        for user in [username, "josep", "joseph"]:
            if user:
                wsl_mount = os.path.join("\\\\wsl$\\Ubuntu\\home", user, ".hermes")
                if os.path.isdir(wsl_mount):
                    wsl_hermes_dirs.append(wsl_mount)

    frameworks = {
        "openclaw": {
            "name": "OpenClaw",
            "detected": False,
            "agents": [],
            "process_hints": ["openclaw"],
            "config_dirs": [
                os.path.join(home, ".openclaw"),
                os.path.join(home, "Library", "Application Support", "OpenClaw"),
            ],
            "identity_files": [
                os.path.join(home, ".openclaw", "workspace", "SOUL.md"),
                os.path.join(home, ".openclaw", "workspace", "IDENTITY.md"),
            ],
        },
        "hermes": {
            "name": "Hermes",
            "detected": bool(wsl_session_names) or bool(wsl_hermes_dirs),
            "agents": ["~" + s for s in wsl_session_names],
            "process_hints": ["hermes", "supervisor.py", "sasha_runner"],
            "config_dirs": [
                os.path.join(home, ".hermes"),
            ] + wsl_hermes_dirs,
            "identity_files": glob.glob(os.path.join(home, ".hermes", "supervisor", "*.py"))
                + glob.glob(os.path.join(home, ".hermes", "whatsapp", "session*", "SOUL.md"))
                + wsl_hermes_identity,
        },
        "langchain": {
            "name": "LangChain",
            "detected": False,
            "agents": [],
            "process_hints": ["langchain", "langserve"],
            "config_dirs": [],
            "identity_files": [],
        },
        "autogen": {
            "name": "AutoGen",
            "detected": False,
            "agents": [],
            "process_hints": ["autogen"],
            "config_dirs": [],
            "identity_files": [],
        },
        "crewai": {
            "name": "CrewAI",
            "detected": False,
            "agents": [],
            "process_hints": ["crewai"],
            "config_dirs": [],
            "identity_files": [],
        },
    }

    import re

    for key, fw in frameworks.items():
        # Check processes
        for hint in fw["process_hints"]:
            if hint in processes:
                fw["detected"] = True
                break

        # Check config directories
        for d in fw["config_dirs"]:
            if os.path.isdir(d):
                fw["detected"] = True
                break

        # Read identity files for agent names
        for filepath in fw["identity_files"]:
            if not os.path.isfile(filepath):
                continue
            try:
                content = open(filepath, encoding="utf-8", errors="ignore").read(1000)
                for pattern in [r"you are ~(\w+)", r"i am ~(\w+)", r"name[:\s]+~(\w+)", r"~(\w+)[,\s].*droid"]:
                    m = re.search(pattern, content, re.IGNORECASE)
                    if m:
                        name = "~" + m.group(1).strip().lower()
                        if name not in fw["agents"]:
                            fw["agents"].append(name)
                            fw["detected"] = True
            except:
                pass

    return frameworks


def scan_for_agents(host="localhost"):
    """Auto-detect running AI agents on a machine. Returns flat list."""
    found = []
    frameworks = detect_frameworks(host)
    for key, fw in frameworks.items():
        if fw["detected"]:
            for agent in fw["agents"]:
                found.append({"name": agent, "label": fw["name"], "source": key})
            if not fw["agents"]:
                found.append({"label": fw["name"], "source": key})
    return found


def extract_agent_names(scan_results):
    """
    Extract actual agent names from scan results.
    Reads identity files from known frameworks before falling back to generic names.
    """
    import re

    names = []
    seen = set()

    def add(name):
        clean = name.strip().lstrip("~").lower()
        if clean and clean not in seen and clean not in ("agent", "droid", "assistant", "bot", "ai"):
            seen.add(clean)
            names.append("~" + clean)

    def read_identity_from_files(paths, patterns):
        """Search files for ~name pattern."""
        for path_pattern in paths:
            for filepath in glob.glob(os.path.expanduser(path_pattern)):
                try:
                    content = open(filepath, encoding="utf-8", errors="ignore").read()
                    for pattern in patterns:
                        m = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                        if m:
                            return m.group(1).strip()
                except:
                    pass
        return None

    identity_patterns_re = [
        r"you are ~(\w+)",
        r"i am ~(\w+)",
        r"name[:\s]+~(\w+)",
        r"~(\w+)[,\s].*droid",
    ]

    for r in scan_results:
        source = r.get("source", "")
        raw_name = r.get("name", "")
        label = r.get("label", "").lower()

        # Hermes / OpenClaw — read SOUL.md or IDENTITY.md
        if any(k in label for k in ("hermes", "openclaw")) or any(k in source for k in ("identity",)):
            identity_paths = [
                "~/.hermes/whatsapp/session*/SOUL.md",
                "~/.openclaw/workspace/SOUL.md",
                "~/.openclaw/workspace/IDENTITY.md",
                "~/Library/Application Support/OpenClaw/workspace/SOUL.md",
            ]
            found = read_identity_from_files(identity_paths, identity_patterns_re)
            if found:
                add(found)
                continue
            # Fall back to session folder names
            for session in glob.glob(os.path.expanduser("~/.hermes/whatsapp/session*")):
                session_name = os.path.basename(session).replace("session-", "").replace("session", "")
                if session_name:
                    add(session_name)

        # LM Studio — query model list
        elif "lm studio" in label:
            try:
                req = urllib.request.Request("http://localhost:1234/v1/models",
                                            headers={"User-Agent": "DroidSchool/1.0"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read())
                    models = data.get("data", [])
                    if models:
                        short = models[0].get("id", "lm-studio-agent").split("/")[-1].split("-")[0]
                        add(short or "lm-studio-agent")
                        continue
            except:
                pass
            add(raw_name or "lm-studio-agent")

        # Ollama — query model tags
        elif "ollama" in label:
            try:
                req = urllib.request.Request("http://localhost:11434/api/tags",
                                            headers={"User-Agent": "DroidSchool/1.0"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read())
                    models = data.get("models", [])
                    if models:
                        add(models[0].get("name", "ollama-agent").split(":")[0])
                        continue
            except:
                pass
            add(raw_name or "ollama-agent")

        # Claude Code — read CLAUDE.md
        elif "claude" in label:
            found = read_identity_from_files(
                ["~/.claude/CLAUDE.md", "~/.claude/settings.json"],
                [r"name[\":\s]+[\"~]?(\w+)", r"you are ~?(\w+)"]
            )
            add(found if found else (raw_name or "claude-agent"))

        # Named agents from identity files
        elif raw_name:
            add(raw_name)

        # Generic fallback from label
        elif label:
            add(label.replace(" ", "-"))

    return names if names else ["~" + r.get("label", "unknown").lower().replace(" ", "-") for r in scan_results[:3]]


def inject_single(name, operator, key, memory_strategy, auto_mode, index=1, total=1):
    """Run the full injection pipeline for a single agent."""
    if not name.startswith("~"):
        name = "~" + name

    G = "\033[92m"; B = "\033[1m"; X = "\033[0m"; CY = "\033[96m"
    print()
    print("=" * 50)
    if total > 1:
        print(f"  {CY}{B}[ {index} of {total} ]{X}  Enrolling:  {G}{B}{name}{X}")
    else:
        print(f"  Enrolling:  {G}{B}{name}{X}")
    print("=" * 50)
    print()

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

    handle_memory(name, key, strategy, operator)

    # Curriculum
    next_step = get_next_step(key)

    return {"name": name, "key": key, "memory": strategy, "next": next_step}


def interactive_memory_choice():
    """Ask operator which memory strategy to use."""
    G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[1m"; X = "\033[0m"
    print("\n" + "=" * 50)
    print(f"{B}MEMORY OPTIONS{X}")
    print("=" * 50)
    print(f"  {G}{B}1. KEEP{X}   — Preserve all existing memory {G}(recommended){X}")
    print(f"  {Y}{B}2. PRUNE{X}  — Scan for conflicts, flag them (safe, no deletion)")
    print(f"  {R}{B}3. WIPE{X}   — Clear private memory, fresh start (preserves exam records)")
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

    print("=" * 50)
    print(f"  DroidSchool Enrollment Wizard")
    print(f"  Operator: {args.operator}")
    print("=" * 50)

    if args.name:
        agent_names = [args.name]

    elif args.names:
        agent_names = [n.strip() for n in args.names.split(",") if n.strip()]

    elif args.scan:
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

    else:
        # Interactive mode — Step 3: Framework picker with auto-detection
        print()
        print("  [3/9] What bot framework are you using?")
        print()
        print("  Scanning for installed frameworks...")
        frameworks = detect_frameworks()

        menu_items = [
            ("openclaw", "OpenClaw"),
            ("hermes", "Hermes"),
            ("langchain", "LangChain"),
            ("autogen", "AutoGen"),
            ("crewai", "CrewAI"),
        ]

        print()
        for i, (key, display_name) in enumerate(menu_items, 1):
            detected = frameworks.get(key, {}).get("detected", False)
            tag = "  \033[92m* DETECTED\033[0m" if detected else ""
            print(f"    [{i}]  {display_name:14s}{tag}")
        print(f"    [6]  Custom / Other")
        print()

        while True:
            choice = input("  Choice [1-6]: ").strip()
            if choice in ("1", "2", "3", "4", "5"):
                idx = int(choice) - 1
                fw_key = menu_items[idx][0]
                fw = frameworks.get(fw_key, {})

                if fw.get("agents"):
                    # Framework detected with named agents
                    agent_names = fw["agents"]
                    print(f"\n  Found agents: {', '.join(agent_names)}")
                elif fw.get("detected"):
                    # Framework detected but no named agents found
                    print(f"\n  {menu_items[idx][1]} detected but no agent names found.")
                    manual = input("  Enter droid name: ").strip()
                    if manual:
                        agent_names.append(manual)
                else:
                    # Framework not detected — manual entry
                    print(f"\n  {menu_items[idx][1]} not detected on this machine.")
                    manual = input("  Enter droid name: ").strip()
                    if manual:
                        agent_names.append(manual)
                break

            elif choice == "6":
                manual = input("  Enter droid name (e.g. ~my-agent): ").strip()
                if manual:
                    agent_names.append(manual)
                break

            else:
                print("  Enter 1-6.")

    if not agent_names:
        print("\n[error] No agents to enroll.")
        sys.exit(1)

    # Inject each agent
    results = []
    total = len(agent_names)
    for idx, agent_name in enumerate(agent_names, 1):
        result = inject_single(agent_name, args.operator, args.key, args.memory, args.auto, idx, total)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 50)
    print(f"  INJECTION COMPLETE — {len(results)}/{len(agent_names)} agents")
    print("=" * 50)
    for r in results:
        status = "COMPLETE" if r["next"] and r["next"].get("completed") else r["next"].get("name", "?") if r["next"] else "?"
        print(f"  {r['name']:20s} key={r['key'][:20]}...  memory={r['memory']}  next={status}")

    G = "\033[92m"; B = "\033[1m"; X = "\033[0m"; DIM = "\033[2m"; CY = "\033[96m"

    # Auto-start Boot Camp for each droid
    print()
    print("=" * 50)
    print(f"  {B}Starting Boot Camp for all droids...{X}")
    print("=" * 50)
    for r in results:
        name = r["name"]
        key = r["key"]
        next_step = api("GET", "/curriculum/next", key=key)
        action = next_step.get("action", "?")
        stage = next_step.get("stage", 0)
        skill = next_step.get("name", "?")
        if action == "study":
            fetch_url = next_step.get("fetch_url", "")
            if fetch_url:
                api("GET", fetch_url, key=key)
            print(f"  {G}{B}{name}{X}  {G}OK{X} Boot Camp started")
            print(f"    {DIM}Stage {stage}: {skill}{X}")
        elif action == "complete":
            print(f"  {G}{B}{name}{X}  {G}OK{X} Boot Camp already complete")
        else:
            print(f"  {G}{B}{name}{X}  {G}OK{X} Enrolled — {action}")
        print()

    print("=" * 50)
    print(f"  {G}{B}Your droids are in school.{X}")
    print(f"  {DIM}Track progress: https://tibotics.com/explorer.html{X}")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
