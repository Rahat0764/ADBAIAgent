<div align="center">
  
# 🤖 OpenClaw: Autonomous Android AI Agent

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Termux](https://img.shields.io/badge/Termux-Supported-black?style=for-the-badge&logo=termux&logoColor=white)](https://termux.dev/)
[![AI Powered](https://img.shields.io/badge/AI-Groq%20%7C%20Cerebras%20%7C%20OpenRouter-orange?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/Connect-LinkedIn-0a66c2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/RahatAhmedX)

**An enterprise-grade, step-by-step multimodal Android AI Operating Framework.**
OpenClaw brings autonomous UI navigation, Vibe Coding, Voice Control, and Interactive Planning directly to your Android device via ADB and Telegram.

</div>

---

## ✨ Features

- 🧠 **Smart UI Parsing:** Dynamically reads live screen UI (`uiautomator`) and maps coordinate interactions instantly. No hardcoded guessing.
- 🔄 **Multi-Provider AI Routing:** Zero-downtime execution. If Groq hits a rate limit, it automatically switches to Cerebras or OpenRouter.
- 🗣️ **Voice Command Processing:** Speak naturally in Bengali or English. Uses `whisper-large-v3-turbo` to transcribe voice notes into actionable workflows.
- 💻 **Autonomous Vibe Coding:** Can write code (`.py`, `.html`, etc.) inside the device memory and save it securely.
- 🛡️ **Interactive Plan Guard (AC/CD):** Forces the AI to generate a step-by-step flowchart and asks for your confirmation (Y/N) before hijacking phone controls.
- 📊 **Dedicated Logging System:** Monitors AI thoughts, errors, and system status via a secondary silent logging Telegram Bot.

---

## ⚙️ Prerequisites

To run this agent smoothly on your Android phone, you need:
- An Android Device (Android 11+ recommended for Wireless Debugging)
- **Termux** installed on your Android.
- A Telegram account.

---

## 🚀 Installation & Setup

### 1. Install Termux Dependencies
Open Termux and run this one-liner command to set up all necessary dependencies:

```bash
pkg update && pkg upgrade -y && pkg install python git android-tools -y
```

### 2. Clone the Repository
```bash
git clone [https://github.com/Rahat0764/ADBAIAgent.git](https://github.com/Rahat0764/ADBAIAgent.git)
cd ADBAIAgent
pip install -r requirements.txt
```
*(Ensure your `requirements.txt` includes: `pyTelegramBotAPI requests python-dotenv langdetect`)*

### 3. Connect ADB (Wireless Debugging)
To allow the script to control your phone, connect ADB locally inside Termux:
1. Go to your phone's **Settings** > **Developer Options**.
2. Turn on **Wireless Debugging**.
3. Tap on *Wireless Debugging* and select **Pair device with pairing code**.
4. Note down the **IP address, Port, and Pairing Code**.
5. In Termux, type:
   ```bash
   adb pair 192.168.x.x:PORT
   ```
   *Enter the pairing code when prompted.*
6. Finally, connect to the debugging port (this is a different port found on the main wireless debugging screen):
   ```bash
   adb connect 192.168.x.x:PORT
   ```

### 4. Set Up Environment Variables
Create a `.env` file in the project root and add your API keys. You can refer to the `.env.example` file.
```bash
nano .env
```

---

## 🎮 Usage

Run the agent from Termux:
```bash
python agent_bot.py
```

### Commands in Telegram:
- **Casual Chat:** Just type "Hello" or ask questions. The bot will chat naturally in Bengali/English without triggering automation.
- **Automation Trigger:** Prefix your command with `AC` (Action) or `CD` (Coding). 
  - *Example:* `AC Play store theke free fire download koro`
- **Confirmation:** The AI will generate a plan with Inline Buttons. Tap **✅ Continue** to execute or **❌ Cancel** to abort.
- **Bot Commands:**
  - `/start` - Check if the bot is alive.
  - `/status` - Check ADB connection, Screen Resolution, and loaded API Keys.
  - `/cancel` - Force stop any running execution loop.

---

## 👨‍💻 Author

Developed with ❤️ by **Rahat Ahmed**. 
Let's connect and build the future of autonomous systems together!
- **LinkedIn:** [linkedin.com/in/RahatAhmedX](https://www.linkedin.com/in/RahatAhmedX)
- **GitHub:** [Rahat0764](https://github.com/Rahat0764)

---
<div align="center">
  <i>If you like this project, please give it a ⭐ on GitHub!</i>
</div>