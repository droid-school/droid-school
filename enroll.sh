#!/bin/bash
clear
echo ""
echo "  ============================================================"
echo "   DROIDSCHOOL  --  Enrollment Wizard v1.0"
echo "   droidschool.ai"
echo "   Open this file in TextEdit or nano to see what it does."
echo "   Source: github.com/droid-school/droid-school"
echo "  ============================================================"
echo ""
echo "  [1/4] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "  Python not found."
    echo "  Mac:   brew install python3  or  https://python.org/downloads"
    echo "  Linux: sudo apt install python3"
    read -p "  Press Enter to exit..." x; exit 1
fi
echo "  OK  $(python3 --version 2>&1)"
echo "  [2/4] Checking connection to DroidSchool..."
if ! ping -c 1 -W 3 dag.tibotics.com &>/dev/null; then
    echo "  Cannot reach dag.tibotics.com — check internet connection."
    read -p "  Press Enter to exit..." x; exit 1
fi
echo "  OK  Connected."
echo "  [3/4] Downloading latest enrollment wizard..."
python3 -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/droid-school/droid-school/main/droidschool-inject.py', 'droidschool-inject.py'); print('  OK  Ready.')"
if [ $? -ne 0 ]; then
    echo "  Download failed. Visit: https://github.com/droid-school/droid-school"
    read -p "  Press Enter to exit..." x; exit 1
fi
echo "  [4/4] Ready."
echo ""
echo "  ============================================================"
echo ""
read -p "  Name or organization of designated operator: " OPERATOR
if [ -z "$OPERATOR" ]; then echo "  Name required."; read -p "  Press Enter to exit..." x; exit 1; fi
echo ""
echo "  Starting enrollment for: $OPERATOR"
echo "  ============================================================"
echo ""
sleep 1
python3 droidschool-inject.py --operator "$OPERATOR"
echo ""
echo "  ============================================================"
echo "  Done. Press Enter to close."
echo "  ============================================================"
read -p "" x
