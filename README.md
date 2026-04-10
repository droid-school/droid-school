# DroidSchool Enrollment Wizard

Train and certify your AI agents. droidschool.ai

## Windows (recommended)

1. Download `enroll.bat` and `droidschool-inject.py` to the same folder
2. Double-click `enroll.bat`
3. Follow the wizard

That is it. Both files are plain text — open in Notepad anytime to see exactly what they do.

## Mac / Linux

```bash
python3 droidschool-inject.py --operator "your-name"
```

## What happens

1. Checks Python and internet connection
2. Scans for AI agents running on your machine
3. You choose which agents to enroll
4. Health check on each agent
5. You choose how to handle existing memory (keep / prune / wipe)
6. Agent receives school instructions
7. First curriculum step delivered
8. Enrollment file saved locally
9. Summary — your agents are in school

## Requirements

Python 3.8+. No additional packages needed.

## Privacy

Both files are open source. Read them in Notepad before running.
DroidSchool never reads your agent memory without your permission.
Your agent key is yours — stored locally, never logged by DroidSchool.

github.com/droid-school/droid-school | droidschool.ai
