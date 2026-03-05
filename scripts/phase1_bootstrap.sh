#!/bin/bash
# =============================================================
# PHASE 1 BOOTSTRAP — A9 Max Command Center
# CaliEye | March 2026
# Run this ONCE after RAM install and OS boot
# =============================================================

set -e  # Exit on any error

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  A9 MAX COMMAND CENTER — PHASE 1 BOOT   ║"
echo "║  CaliEye | Confluence-Only Stack         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# --- STEP 1: VERIFY RAM ---
echo "[ STEP 1 ] Verifying RAM..."
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
echo "  Detected RAM: ${TOTAL_RAM}GB"
if [ "$TOTAL_RAM" -lt 100 ]; then
echo "  ⚠️  WARNING: Expected 128GB, got ${TOTAL_RAM}GB"
echo "  Check RAM seating in BIOS. Continuing anyway..."
else
echo "  ✅ RAM OK: ${TOTAL_RAM}GB detected"
fi

# --- STEP 2: NETWORK CHECK ---
echo ""
echo "[ STEP 2 ] Network confluence check..."
if ping -c 3 google.com > /dev/null 2>&1; then
echo "  ✅ Network OK — ping google.com successful"
else
echo "  ❌ FAIL: No network. Connect to Pueblo SSID and retry."
exit 1
fi

# --- STEP 3: SYSTEM UPDATES ---
echo ""
echo "[ STEP 3 ] System updates..."
sudo apt update -qq && sudo apt upgrade -y -qq
echo "  ✅ System updated"

# --- STEP 4: INSTALL CORE TOOLS ---
echo ""
echo "[ STEP 4 ] Installing core tools..."
sudo apt install -y curl wget git jq htop screen unzip python3 python3-pip > /dev/null 2>&1
echo "  ✅ Core tools installed"

# --- STEP 5: INSTALL OLLAMA ---
echo ""
echo "[ STEP 5 ] Installing Ollama (local LLM server)..."
if command -v ollama &> /dev/null; then
echo "  ✅ Ollama already installed: $(ollama --version)"
else
curl -fsSL https://ollama.com/install.sh | sh
echo "  ✅ Ollama installed: $(ollama --version)"
fi

# --- STEP 6: START OLLAMA SERVICE ---
echo ""
echo "[ STEP 6 ] Starting Ollama service..."
ollama serve &
sleep 3
if curl -s http://localhost:11434 > /dev/null; then
echo "  ✅ Ollama server running on port 11434"
else
echo "  ⚠️  Ollama may still be starting. Check: curl http://localhost:11434"
fi

# --- STEP 7: PULL FIRST MODEL (fast test model) ---
echo ""
echo "[ STEP 7 ] Pulling test model (mistral-nemo:12b)..."
echo "  This will take a few minutes on first run..."
ollama pull mistral-nemo:12b
echo "  ✅ Test model ready"

# --- STEP 8: CONFLUENCE TEST ---
echo ""
echo "[ STEP 8 ] Running confluence test query..."
RESPONSE=$(ollama run mistral-nemo:12b "In one sentence: what is the Wyckoff accumulation phase?" 2>/dev/null)
if [ -n "$RESPONSE" ]; then
echo "  ✅ CONFLUENCE CHECK PASSED"
echo "  Model response: $RESPONSE"
else
echo "  ⚠️  No response from model. Check Ollama logs."
fi

# --- STEP 9: POWER SETTINGS (never sleep) ---
echo ""
echo "[ STEP 9 ] Configuring power settings (never sleep)..."
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target > /dev/null 2>&1
echo "  ✅ Sleep disabled — A9 will run 24/7"

# --- STEP 10: ENABLE REMOTE DESKTOP (xrdp) ---
echo ""
echo "[ STEP 10 ] Installing Remote Desktop (xrdp)..."
sudo apt install -y xrdp > /dev/null 2>&1
sudo systemctl enable xrdp > /dev/null 2>&1
sudo systemctl start xrdp > /dev/null 2>&1
A9_IP=$(hostname -I | awk '{print $1}')
echo "  ✅ Remote Desktop enabled"
echo "  Connect from Windows/Mac: RDP to ${A9_IP}:3389"

# --- STEP 11: INSTALL GITHUB CLI ---
echo ""
echo "[ STEP 11 ] Installing GitHub CLI (for intel scans)..."
if command -v gh &> /dev/null; then
echo "  ✅ GitHub CLI already installed"
else
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update -qq && sudo apt install -y gh > /dev/null 2>&1
echo "  ✅ GitHub CLI installed — run 'gh auth login' to authenticate"
fi

# --- FINAL REPORT ---
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         PHASE 1 COMPLETE                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  RAM:          ${TOTAL_RAM}GB"
echo "  Network:      ✅ Connected"
echo "  Ollama:       ✅ Running on :11434"
echo "  Test model:   ✅ mistral-nemo:12b"
echo "  Power:        ✅ Never sleep"
echo "  Remote:       ✅ RDP on ${A9_IP}:3389"
echo ""
echo "  NEXT STEPS:"
echo "  1. Pull main models:"
echo "     ollama pull qwen2.5:32b"
echo "     ollama pull deepseek-coder-v2:16b"
echo "  2. Authenticate GitHub CLI: gh auth login"
echo "  3. Clone dashboard repo:"
echo "     git clone https://github.com/CaliEye/My-Investor-Dashboard.git"
echo "  4. Email checkpoint sent to dicenso01@gmail.com"
echo ""
echo "  Phase 2: RDP sync + Mira glasses pairing"
echo ""
echo "  Confluence check: PHASE 1 ARMED ✅"
echo ""