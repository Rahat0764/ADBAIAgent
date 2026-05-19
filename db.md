<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=28&pause=1000&color=00D9FF&center=true&vCenter=true&width=600&lines=ADB+AI+Agent;Control+Your+Android+via+Telegram;Powered+by+LLM+%2B+ADB" alt="Typing SVG" />

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![ADB](https://img.shields.io/badge/Android-ADB-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com/tools/adb)
[![Termux](https://img.shields.io/badge/Runs%20on-Termux-000000?style=for-the-badge&logo=gnometerminal&logoColor=white)](https://termux.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Groq](https://img.shields.io/badge/Groq-LPU%20Inference-F55036?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMiIgZmlsbD0id2hpdGUiLz48L3N2Zz4=&logoColor=white)](https://groq.com)
[![Stars](https://img.shields.io/github/stars/Rahat0764/ADBAIAgent?style=for-the-badge&color=FFD700&logo=github)](https://github.com/Rahat0764/ADBAIAgent/stargazers)

<br/>

**A step-by-step AI Agent that controls your Android device through Telegram.**
Send a command → Agent plans → Executes via ADB → Done.

<br/>

[![LinkedIn](https://img.shields.io/badge/Rahat%20Ahmed-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://LinkedIn.com/in/RahatAhmedX)
[![GitHub](https://img.shields.io/badge/Rahat0764-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Rahat0764)

</div>

---

## What is this?

**ADB AI Agent** is a self-hosted Telegram bot that runs on **Termux** and uses an LLM to autonomously control your Android phone via ADB. You describe a task in plain text — the agent thinks, plans, and executes it step-by-step without you touching the screen.

```
You:   AC open YouTube and search for lo-fi music
Bot:   #A3F9B2C1 💭 Plan: Open YouTube → Search → Play
Bot:   [✅ Continue] [❌ Cancel]
       ... executes every step automatically
Bot:   #A3F9B2C1 ✅ Task completed!
```

---

## Features

- **Natural Language Control** — Describe what you want in plain English or Bengali
- **Step-by-Step Planning** — Agent creates a plan before doing anything, you approve it
- **Unique Task IDs** — Every task gets a `#TASKID` so logs and messages are always traceable
- **Inline Confirm Buttons** — One-tap Continue / Cancel, no typing needed
- **Real-Time ADB Display** — Every ADB command shown live: `🔧 adb shell input tap 540 1200`
- **Dedicated Log Bot** — Full raw logs (API responses, reasoning, screen dumps) sent to a separate bot
- **Multi-Provider LLM Fallback** — Groq → Cerebras → OpenRouter, auto-switches on rate limit or failure
- **Voice Commands** — Send a voice note, agent transcribes and executes
- **Screenshot on Demand** — Agent can capture and send the current screen
- **Code Generation** — Agent writes and saves code files to `AIAgent/coding/`
- **Smart Suggestions** — Casual messages get an inline suggestion to automate the task

---

## Architecture

```
Telegram Message
      │
      ▼
 handle_message()
      │
      ├── AC/CD prefix? ──► generate_plan() ──► LLM (PLAN action)
      │                          │
      │                    User taps ✅ Continue
      │                          │
      │                     run_task() ──► LLM loop (up to 50 steps)
      │                          │
      │                   execute_actions()
      │                          │
      │            ┌─────────────┼─────────────┐
      │          TAP          SWIPE        OPEN_APP ...
      │            │             │              │
      │         run_adb()    run_adb()      run_adb()
      │                          │
      │                    send_log() ──► Log Bot
      │
      └── No prefix? ──► handle_casual_chat() ──► LLM (REPLY action)
```

---

## Requirements

- Android phone with **Termux** installed
- **Wireless ADB** enabled on the target device (same Wi-Fi)
- API keys from at least one provider: Groq, Cerebras, or OpenRouter (all free)
- Two Telegram bots: one main bot, one log bot (both from [@BotFather](https://t.me/BotFather))

---

## Installation

### Step 1 — Set up Termux

Install [Termux](https://f-droid.org/packages/com.termux/) from F-Droid (not Play Store).

### Step 2 — Install all dependencies in one command

```bash
pkg update -y && pkg upgrade -y && pkg install -y python android-tools git && pip install pytelegrambotapi requests python-dotenv
```

> This installs Python, ADB (`android-tools`), git, and all Python packages in one shot.

### Step 3 — Grant storage access

```bash
termux-setup-storage
```

### Step 4 — Clone the repository

```bash
git clone https://github.com/Rahat0764/ADBAIAgent.git
cd ADBAIAgent
```

### Step 5 — Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in your `.env` file:

```env
# Main Telegram Bot token (from @BotFather)
BOT_TOKEN=your_main_bot_token

# Log Bot token (separate bot, also from @BotFather)
LOG_BOT_TOKEN=your_log_bot_token

# Chat ID to receive logs (your personal chat ID or a private group)
LOG_CHAT_ID=123456789

# Your Telegram user ID (get it from @userinfobot)
ALLOWED_USERS=123456789

# IP:port of your Android device with wireless ADB enabled
ADB_ADDRESS=192.168.1.100:5555

# API Keys (comma-separated for multiple keys per provider)
GROQ_API_KEYS=gsk_xxxx,gsk_yyyy
CEREBRAS_API_KEYS=
OPENROUTER_API_KEYS=
```

### Step 6 — Enable Wireless ADB on your Android device

On your Android phone (the one you want to control):

1. Go to **Settings → Developer Options**
2. Enable **Wireless debugging**
3. Note the IP address and port shown
4. Set that as `ADB_ADDRESS` in your `.env`

### Step 7 — Run the agent

```bash
python openclaw.py
```

To keep it running after closing Termux:

```bash
nohup python openclaw.py &
```

---

## Usage

| Prefix | Meaning | Example |
|--------|---------|---------|
| `AC ` | Automate a task | `AC open WhatsApp and send Hello to Mom` |
| `CD ` | Automate a task | `CD take a screenshot and send it` |
| *(none)* | Chat normally | `What can you do?` |
| `/status` | Check bot status | `/status` |
| `/cancel` | Stop current task | `/cancel` |

---

## Log Bot Events

Every event sent to your log bot includes a `#TASKID` timestamp and raw data:

| Level | Description |
|-------|-------------|
| `LLM_TRY` | Which provider and model is being attempted |
| `LLM_OK` | Full raw LLM response |
| `API_FAIL` | HTTP status + raw error body from API |
| `API_RATELIMIT` | Rate limit hit with raw response |
| `API_TIMEOUT` | Request timed out |
| `ADB` | Exact command sent + output received |
| `SCREEN_DUMP` | Full UI element list from UIAutomator |
| `REASONING` | Agent's thinking process |
| `TASK_DONE` | Task completed |
| `TASK_ERROR` | Exception trace |

---

## File Structure

```
ADBAIAgent/
├── openclaw.py        # Main agent
├── .env.example       # Environment template
├── .env               # Your config (not committed)
└── README.md

~/storage/shared/AIAgent/
├── coding/            # Code files written by the agent
└── temp/              # Temporary voice & screenshot files (auto-cleaned)
```

---

## LLM Provider Fallback Chain

```
Groq (fastest, free tier)
  └── llama-3.3-70b-versatile
  └── llama3-70b-8192
  └── mixtral-8x7b-32768
  └── llama3-8b-8192
        │ (if all fail or rate limited)
        ▼
Cerebras (fast inference, free tier)
  └── llama3.1-70b
  └── llama3.1-8b
        │ (if all fail)
        ▼
OpenRouter (free models)
  └── meta-llama/llama-3-70b-instruct:free
  └── meta-llama/llama-3-8b-instruct:free
  └── deepseek/deepseek-chat:free
```

All providers have **free tiers**. You need zero paid APIs to run this.

---

## Supported Actions

| Action | Description |
|--------|-------------|
| `PLAN` | Generate execution flowchart |
| `OPEN_APP` | Launch an app by name |
| `SCAN_SCREEN` | Read all UI elements on screen |
| `TAP X Y` | Tap at coordinates |
| `INPUT_TEXT` | Type text |
| `ENTER` | Press enter/search key |
| `SWIPE_UP/DOWN/RIGHT` | Scroll or navigate |
| `HOME` | Go to home screen |
| `BACK` | Press back button |
| `SCREENSHOT` | Capture and send screen |
| `FLASHLIGHT_ON/OFF` | Toggle flashlight |
| `WRITE_CODE` | Generate and save a code file |
| `DONE` | Mark task as complete |

---

## Troubleshooting

**ADB not connecting**
```bash
adb kill-server && adb connect YOUR_IP:PORT
```

**Storage permission denied**
```bash
termux-setup-storage
```

**UIAutomator stuck**
```bash
adb shell pkill -f uiautomator
```

**Bot not responding** — Check your `ALLOWED_USERS` ID is correct. Get yours from [@userinfobot](https://t.me/userinfobot).

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

---

<div align="center">

Made with ❤️ by [Rahat Ahmed](https://LinkedIn.com/in/RahatAhmedX)

[![LinkedIn](https://img.shields.io/badge/Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://LinkedIn.com/in/RahatAhmedX)
[![GitHub](https://img.shields.io/badge/Follow-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Rahat0764)

</div>
