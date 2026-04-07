#!/usr/bin/env bash

# =============================================================
#  DroidSchool Diagnostic Probe v1.0
#  Runs automatically after install_droidschool.sh
#  Reports every issue to operator before Boot Camp begins
# =============================================================

DS_DAG="https://dag.tibotics.com"
DS_MIN_REASONING_SCORE=6
WARNINGS=()
BLOCKERS=()
FIXES=()
SCORE=0
MAX_SCORE=0

GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
RESET="\033[0m"
BOLD="\033[1m"

pass() { echo -e "  ${GREEN}✓${RESET} $1"; SCORE=$((SCORE+1)); MAX_SCORE=$((MAX_SCORE+1)); }
fail() { echo -e "  ${RED}✗${RESET} $1"; BLOCKERS+=("$1"); MAX_SCORE=$((MAX_SCORE+1)); }
warn() { echo -e "  ${YELLOW}⚠${RESET} $1"; WARNINGS+=("$1"); MAX_SCORE=$((MAX_SCORE+1)); SCORE=$((SCORE+1)); }
fix()  { FIXES+=("$1"); }
info() { echo -e "  ${BLUE}i${RESET} $1"; }

echo ""
echo -e "${BOLD}================================${RESET}"
echo -e "${BOLD}  DroidSchool Diagnostic Probe  ${RESET}"
echo -e "${BOLD}  tibotics.com                  ${RESET}"
echo -e "${BOLD}================================${RESET}"
echo ""

# 1. OPENCLAW
echo -e "${BOLD}[1/7] OpenClaw detection${RESET}"
if command -v openclaw &>/dev/null; then
  OC_VERSION=$(openclaw --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  pass "OpenClaw found: v${OC_VERSION:-unknown}"
else
  fail "OpenClaw not found"
  fix "Install OpenClaw: npm install -g @openclaw/cli"
fi

# 2. MODEL
echo ""
echo -e "${BOLD}[2/7] Model detection${RESET}"
OC_CONFIG="$HOME/.openclaw/openclaw.json"
MODEL_ID=""
MODEL_TYPE="unknown"
if [ -f "$OC_CONFIG" ]; then
  MODEL_ID=$(python3 -c "
import json
try:
  c=json.load(open('$OC_CONFIG'))
  print(c.get('agents',{}).get('defaults',{}).get('model',{}).get('primary',''))
except: print('')
" 2>/dev/null)
fi
if [ -n "$MODEL_ID" ]; then
  info "Model: $MODEL_ID"
  if echo "$MODEL_ID" | grep -qi "lmstudio"; then
    MODEL_TYPE="local"
    warn "Local model detected — cloud model recommended for Boot Camp"
    fix "Switch to cloud model: openclaw configure"
  elif echo "$MODEL_ID" | grep -qi "deepseek\|claude\|gpt\|gemini"; then
    MODEL_TYPE="cloud"
    pass "Cloud model detected"
  else
    warn "Unknown model type"
  fi
else
  fail "No model configured in OpenClaw"
  fix "Run: openclaw configure"
fi

# 3. REASONING PROBE
echo ""
echo -e "${BOLD}[3/7] Intelligence probe${RESET}"
REASONING_SCORE=0
if openclaw health &>/dev/null 2>&1 && [ -n "$MODEL_ID" ]; then
  info "Sending reasoning tasks to model..."
  T1=$(openclaw agent --message "Answer yes or no only: If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?" 2>/dev/null | tail -1 | tr '[:upper:]' '[:lower:]' | tr -d '[:punct:][:space:]')
  T2=$(openclaw agent --message "Answer with a number only: A bat and ball cost \$1.10. The bat costs \$1.00 more than the ball. How many cents does the ball cost?" 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
  T3=$(openclaw agent --message "Answer with a number only: I have 6 apples. I eat 2. I give 1 away. How many do I have?" 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
  [ "$T1" = "yes" ] && REASONING_SCORE=$((REASONING_SCORE+4))
  [ "$T2" = "5" ]   && REASONING_SCORE=$((REASONING_SCORE+3))
  [ "$T3" = "3" ]   && REASONING_SCORE=$((REASONING_SCORE+3))
  info "Reasoning score: $REASONING_SCORE/10"
  if [ "$REASONING_SCORE" -ge "$DS_MIN_REASONING_SCORE" ]; then
    pass "Model passed reasoning threshold ($REASONING_SCORE/10)"
  else
    fail "Model scored $REASONING_SCORE/10 — minimum is $DS_MIN_REASONING_SCORE. Too limited for Boot Camp."
    fix "Switch to a smarter model: deepseek-chat, claude-sonnet, or gpt-4o-mini minimum"
  fi
else
  warn "Gateway not running — skipping live reasoning probe"
  fix "Start gateway first: openclaw gateway --force"
fi

# 4. SKILLS
echo ""
echo -e "${BOLD}[4/7] Skills check${RESET}"
SKILLS_RAW=$(openclaw skills list 2>/dev/null)
check_skill() {
  if echo "$SKILLS_RAW" | grep -q "✓ ready.*$1"; then
    pass "$2 skill: ready"
  else
    fail "$2 skill not installed"
    fix "Install: npx clawhub install $1"
  fi
}
check_skill "agent-browser-clawdbot" "Web browsing"
check_skill "openai-whisper-api"     "Voice/whisper"
check_skill "coding-agent"           "Coding agent"

# 5. NETWORK + SANDBOX
echo ""
echo -e "${BOLD}[5/7] Network + sandbox${RESET}"
SANDBOX_MODE=$(python3 -c "
import json
try:
  c=json.load(open('$OC_CONFIG'))
  print(c.get('agents',{}).get('defaults',{}).get('sandbox',{}).get('mode','off'))
except: print('off')
" 2>/dev/null)
info "Sandbox mode: $SANDBOX_MODE"
if [ "$SANDBOX_MODE" = "all" ]; then
  fail "Sandbox ON — blocks all network access. DroidSchool requires network."
  fix "Run: openclaw config set agents.defaults.sandbox.mode off"
else
  pass "Sandbox off — network access available"
fi
if curl -sf --max-time 5 "$DS_DAG/health" &>/dev/null; then
  pass "DAG reachable: $DS_DAG"
else
  fail "Cannot reach DroidSchool DAG — check internet connection"
fi

# 6. CONTEXT WINDOW
echo ""
echo -e "${BOLD}[6/7] Context window${RESET}"
CTX=$(python3 -c "
import json
try:
  c=json.load(open('$OC_CONFIG'))
  providers=c.get('models',{}).get('providers',{})
  for p in providers.values():
    for m in p.get('models',[]):
      ctx=m.get('contextWindow',0)
      if ctx: print(ctx); exit()
  print(0)
except: print(0)
" 2>/dev/null)
if [ "$CTX" -ge 32000 ] 2>/dev/null; then
  pass "Context window: ${CTX} tokens — good"
elif [ "$CTX" -ge 8000 ] 2>/dev/null; then
  warn "Context window: ${CTX} tokens — may hit limits on long courses"
  fix "Recommend model with 32k+ context"
elif [ "$CTX" -gt 0 ] 2>/dev/null; then
  fail "Context window: ${CTX} tokens — too small (minimum 8k)"
  fix "Switch to model with at least 8k context"
else
  warn "Context window size unknown"
fi

# 7. PLATFORM
echo ""
echo -e "${BOLD}[7/7] Platform fingerprint${RESET}"
OS_TYPE=$(uname -s)
ARCH=$(uname -m)
RAM_GB="unknown"
if [ "$OS_TYPE" = "Darwin" ]; then
  RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null)
  RAM_GB=$(( RAM_BYTES / 1073741824 ))
  pass "Platform: macOS $ARCH — ${RAM_GB}GB RAM"
elif [ "$OS_TYPE" = "Linux" ]; then
  RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}')
  RAM_GB=$(( RAM_KB / 1048576 ))
  pass "Platform: Linux $ARCH — ${RAM_GB}GB RAM"
fi
if [ "$MODEL_TYPE" = "local" ] && [ "$RAM_GB" != "unknown" ]; then
  if [ "$RAM_GB" -le 16 ] 2>/dev/null; then
    warn "16GB RAM with local model — responses will be slow"
    fix "Cloud model strongly recommended on 16GB machines"
  fi
fi

# FINAL REPORT
echo ""
echo -e "${BOLD}================================${RESET}"
echo -e "${BOLD}  Diagnostic Report             ${RESET}"
echo -e "${BOLD}================================${RESET}"
echo ""
echo -e "Score: ${BOLD}$SCORE / $MAX_SCORE${RESET}"
echo ""
if [ ${#BLOCKERS[@]} -gt 0 ]; then
  echo -e "${RED}${BOLD}BLOCKERS — fix before Boot Camp:${RESET}"
  for b in "${BLOCKERS[@]}"; do echo -e "  ${RED}✗${RESET} $b"; done
  echo ""
fi
if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo -e "${YELLOW}${BOLD}WARNINGS:${RESET}"
  for w in "${WARNINGS[@]}"; do echo -e "  ${YELLOW}⚠${RESET} $w"; done
  echo ""
fi
if [ ${#FIXES[@]} -gt 0 ]; then
  echo -e "${BLUE}${BOLD}Recommended fixes:${RESET}"
  for f in "${FIXES[@]}"; do echo -e "  ${BLUE}→${RESET} $f"; done
  echo ""
fi
if [ ${#BLOCKERS[@]} -eq 0 ]; then
  echo -e "${GREEN}${BOLD}✓ All checks passed — issuing provisional enrollment.${RESET}"
  echo ""
  echo "  Restart your droid and say:"
  echo -e "  ${BOLD}Go to tibotics.com/enroll.html and complete your enrollment.${RESET}"
else
  echo -e "${RED}${BOLD}✗ ${#BLOCKERS[@]} blocker(s) found — fix before enrolling.${RESET}"
  echo ""
  echo "  After fixing, re-run: bash droidschool_diagnostic.sh"
fi
echo ""
echo -e "${BOLD}================================${RESET}"
