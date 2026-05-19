import telebot
import requests
import subprocess
import xml.etree.ElementTree as ET
import re
import time
import os
import threading
import html
import uuid
from datetime import datetime
from dotenv import load_dotenv
from telebot import types

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
LOG_BOT_TOKEN = os.getenv('LOG_BOT_TOKEN')
LOG_CHAT_ID = int(os.getenv('LOG_CHAT_ID', '0'))
ALLOWED_USERS = [int(i.strip()) for i in os.getenv('ALLOWED_USERS', '').split(',') if i.strip()]
ADB_ADDRESS = os.getenv('ADB_ADDRESS', '')

def get_keys(env_var):
    raw = os.getenv(env_var, '')
    return [k.strip() for k in raw.split(',') if k.strip()]

GROQ_KEYS = get_keys('GROQ_API_KEYS')
CEREBRAS_KEYS = get_keys('CEREBRAS_API_KEYS')
OPENROUTER_KEYS = get_keys('OPENROUTER_API_KEYS')

if not GROQ_KEYS and not CEREBRAS_KEYS and not OPENROUTER_KEYS:
    print("[FATAL]: No API keys found.")
    exit(1)

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "llama3-8b-8192"
]
CEREBRAS_MODELS = ["llama3.1-70b", "llama3.1-8b"]
OPENROUTER_MODELS = [
    "meta-llama/llama-3-70b-instruct:free",
    "meta-llama/llama-3-8b-instruct:free",
    "deepseek/deepseek-chat:free"
]
AUDIO_MODEL = "whisper-large-v3-turbo"

PROVIDERS = []
if GROQ_KEYS:
    for model in GROQ_MODELS:
        for key in GROQ_KEYS:
            PROVIDERS.append(("https://api.groq.com/openai/v1/chat/completions", key, model, "Groq"))
if CEREBRAS_KEYS:
    for model in CEREBRAS_MODELS:
        for key in CEREBRAS_KEYS:
            PROVIDERS.append(("https://api.cerebras.ai/v1/chat/completions", key, model, "Cerebras"))
if OPENROUTER_KEYS:
    for model in OPENROUTER_MODELS:
        for key in OPENROUTER_KEYS:
            PROVIDERS.append(("https://openrouter.ai/api/v1/chat/completions", key, model, "OpenRouter"))

AIAGENT_DIR = os.path.join(os.path.expanduser("~"), "storage", "shared", "AIAgent")
SAVE_DIR = os.path.join(AIAGENT_DIR, "coding")
TEMP_DIR = os.path.join(AIAGENT_DIR, "temp")
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
log_bot = telebot.TeleBot(LOG_BOT_TOKEN, threaded=True) if LOG_BOT_TOKEN else None

_lock = threading.Lock()
_agent_busy = False
_cancel_event = threading.Event()
_screen_width = 1080
_screen_height = 2400
_active_task: dict = {}

VALID_ACTIONS = {
    "PLAN", "OPEN_APP", "HOME", "BACK", "SWIPE_UP", "SWIPE_DOWN", "SWIPE_RIGHT",
    "SCAN_SCREEN", "TAP", "INPUT_TEXT", "ENTER", "FLASHLIGHT_ON", "FLASHLIGHT_OFF",
    "WRITE_CODE", "SCREENSHOT", "DONE", "REPLY", "API_ERROR"
}

APP_MAP = {
    "play store": "com.android.vending",
    "google play": "com.android.vending",
    "youtube": "com.google.android.youtube",
    "yt": "com.google.android.youtube",
    "chrome": "com.android.chrome",
    "browser": "com.android.chrome",
    "settings": "com.android.settings",
    "facebook": "com.facebook.katana",
    "whatsapp": "com.whatsapp",
    "messenger": "com.facebook.orca"
}

_SKIP_NAMES = {"ESC", "CTRL", "ALT", "HOME", "END", "PGUP", "PGDN", "TAB", "DEL", "INS"}
_SAFE_TEXT = re.compile(r"^[\w\s\u0980-\u09FF\-_.,!?@#':\s]+$")
_ACTION_KEYWORDS = ["খোলো", "চালু", "বন্ধ", "যাও", "দেখাও", "নাও", "পাঠাও", "সার্চ",
                    "open", "start", "go to", "search", "send", "show", "launch", "play"]

SYSTEM_PROMPT = """You are ADB AI Agent, a highly robust step-by-step Android AI Agent. Master: Rahat.

AVAILABLE ACTIONS:
<action>PLAN</action>               -> Generate a step-by-step flowchart/plan before starting the task. (MUST DO THIS FIRST FOR AUTOMATION TASKS)
<action>OPEN_APP app_name</action>  -> Quick launch app.
<action>HOME</action>               -> Go to Home Screen
<action>SWIPE_UP</action>           -> Scroll up
<action>SWIPE_DOWN</action>         -> Scroll down
<action>SWIPE_RIGHT</action>        -> Swipe right
<action>SCAN_SCREEN</action>        -> Read current live screen elements. (MANDATORY before any TAP).
<action>TAP X Y</action>            -> Tap on exact coordinates (Example: TAP 500 1200)
<action>INPUT_TEXT text</action>    -> Type text. ALWAYS PURE ENGLISH (Latin Script). NEVER Bengali.
<action>ENTER</action>              -> Press Enter/Search on keyboard
<action>BACK</action>               -> Press Back button
<action>FLASHLIGHT_ON</action>      -> Turn flashlight ON
<action>FLASHLIGHT_OFF</action>     -> Turn flashlight OFF
<action>WRITE_CODE filename.ext</action> -> Create any coding file.
<action>SCREENSHOT</action>         -> Take a live screenshot.
<action>REPLY</action>              -> Just reply to the user without doing any actions.
<action>DONE</action>               -> Task Completed.

CRITICAL RULES:
1. You MUST ALWAYS write your <think> plans and chat replies in Native Bengali Script.
2. If user just chats, output <action>REPLY</action>.
3. For automation tasks (AC or CD), your very first action MUST BE <action>PLAN</action>.
4. Output EXACTLY ONE action inside <action>...</action> tags per response.
5. You MUST execute <action>SCAN_SCREEN</action> after EVERY transition before you tap anything.
6. Never guess coordinates."""


def new_task_id() -> str:
    return uuid.uuid4().hex[:8].upper()

def set_busy(val: bool):
    global _agent_busy
    with _lock:
        _agent_busy = val

def is_busy() -> bool:
    with _lock:
        return _agent_busy

def is_authorized(uid: int) -> bool:
    return uid in ALLOWED_USERS

def safe_html(text: str) -> str:
    cleaned = html.escape(text)
    cleaned = re.sub(r'&lt;b&gt;(.*?)&lt;/b&gt;', r'<b>\1</b>', cleaned)
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cleaned)
    cleaned = re.sub(r'_(.*?)_', r'<i>\1</i>', cleaned)
    cleaned = re.sub(r'&lt;blockquote&gt;(.*?)&lt;/blockquote&gt;', r'<blockquote>\1</blockquote>', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'&lt;code&gt;(.*?)&lt;/code&gt;', r'<code>\1</code>', cleaned)
    return cleaned

def tag(task_id: str) -> str:
    return f"<code>#{task_id}</code>"

def send_log(task_id: str, level: str, content: str):
    if not log_bot or not LOG_CHAT_ID:
        return
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        msg = (
            f"[{ts}] <b>[{level}]</b> <code>#{task_id}</code>\n"
            f"<pre>{html.escape(str(content)[:3500])}</pre>"
        )
        log_bot.send_message(LOG_CHAT_ID, msg, parse_mode="HTML")
    except Exception:
        pass

def run_adb(*args: str) -> tuple[bool, str]:
    cmd = ["adb", "shell"] + list(args)
    for attempt in range(2):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            out = result.stdout.strip()
            err = result.stderr.strip()
            if "no devices" in out or "no devices" in err or "disconnected" in err:
                if ADB_ADDRESS and attempt == 0:
                    subprocess.run(["adb", "connect", ADB_ADDRESS], capture_output=True, timeout=5)
                    continue
                return False, "ERROR: ADB disconnected."
            return True, out
        except subprocess.TimeoutExpired:
            return False, "ERROR: ADB command timed out."
        except Exception as e:
            return False, f"ERROR: {e}"
    return False, "ERROR: ADB failed after reconnect."

def run_adb_raw(*args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(["adb"] + list(args), capture_output=True, text=True, timeout=10)
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def run_adb_action(chat_id: int, task_id: str, *args: str) -> tuple[bool, str]:
    cmd_str = "adb shell " + " ".join(str(a) for a in args)
    ok, res = run_adb(*args)
    bot.send_message(
        chat_id,
        f"{tag(task_id)} 🔧 <code>{html.escape(cmd_str)}</code>",
        parse_mode="HTML"
    )
    send_log(task_id, "ADB", f"CMD: {cmd_str}\nOUT: {res}\nOK: {ok}")
    if not ok:
        bot.send_message(chat_id, f"{tag(task_id)} ⚠️ <b>ADB Error:</b> <code>{html.escape(res)}</code>", parse_mode="HTML")
    return ok, res

def get_current_app_focus() -> str:
    ok, output = run_adb("dumpsys", "window", "windows")
    if not ok:
        return "Unknown"
    for line in output.splitlines():
        if "mCurrentFocus" in line:
            for pattern in [r'u\d+\s+([^\s/]+)', r'Window\{[^\s]+\s+([^\s/]+)', r'([a-zA-Z0-9._]+)/[a-zA-Z0-9._]+']:
                m = re.search(pattern, line)
                if m:
                    return m.group(1)
    return "Unknown"

def scan_screen() -> str:
    run_adb("rm", "-f", "/data/local/tmp/w.xml")
    ok, _ = run_adb("uiautomator", "dump", "/data/local/tmp/w.xml")
    if not ok:
        run_adb("pkill", "-f", "uiautomator")
        time.sleep(1.5)
        ok, _ = run_adb("uiautomator", "dump", "/data/local/tmp/w.xml")
        if not ok:
            return "ERROR: UIAutomator failed. Try SCAN_SCREEN again."

    ok, xml_out = run_adb("cat", "/data/local/tmp/w.xml")
    if not ok or not xml_out.strip() or "No such file" in xml_out:
        time.sleep(2)
        run_adb("uiautomator", "dump", "/data/local/tmp/w.xml")
        ok, xml_out = run_adb("cat", "/data/local/tmp/w.xml")
        if not ok or not xml_out.strip():
            return "ERROR: Screen layout not ready. Try SCAN_SCREEN again."

    if not xml_out.strip().startswith("<?xml"):
        s = xml_out.find("<")
        e = xml_out.rfind(">")
        if s != -1 and e != -1:
            xml_out = xml_out[s:e+1]

    try:
        tree = ET.fromstring(xml_out)
    except ET.ParseError:
        return "ERROR: Could not parse screen XML."

    seen, elements = set(), []
    for node in tree.iter('node'):
        name = (node.attrib.get('text', '') or node.attrib.get('content-desc', '')).strip()
        bounds = node.attrib.get('bounds', '')
        if not name or not bounds or name in seen or name in _SKIP_NAMES:
            continue
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            cx, cy = (x1+x2)//2, (y1+y2)//2
            seen.add(name)
            elements.append(f"'{name}' -> TAP {cx} {cy}")

    if not elements:
        return "Screen has no tappable elements. Page may still be loading."

    return f"Active App: {get_current_app_focus()}\n\nLive UI Elements:\n" + "\n".join(elements[:40])

def lock_portrait_mode():
    run_adb("content", "insert", "--uri", "content://settings/system",
            "--bind", "name:s:accelerometer_rotation", "--bind", "value:i:0")
    run_adb("content", "insert", "--uri", "content://settings/system",
            "--bind", "name:s:user_rotation", "--bind", "value:i:0")

def connect_adb_on_startup() -> str | None:
    global _screen_width, _screen_height
    if not ADB_ADDRESS:
        return None
    print(f"[ADB]: Connecting to {ADB_ADDRESS}...")
    subprocess.run(["adb", "connect", ADB_ADDRESS], capture_output=True, timeout=8)
    lock_portrait_mode()
    ok, size_out = run_adb_raw("shell", "wm", "size")
    if ok:
        m = re.search(r'Physical size: (\d+)x(\d+)', size_out)
        if m:
            _screen_width, _screen_height = int(m.group(1)), int(m.group(2))
            print(f"[ADB]: Resolution: {_screen_width}x{_screen_height}")
    ok, model = run_adb_raw("shell", "getprop", "ro.product.model")
    if ok and model and "no devices" not in model:
        return model
    return None

def call_provider(messages: list, url: str, key: str, model: str, name: str, task_id: str) -> str | None:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if "openrouter" in url:
        headers["HTTP-Referer"] = "https://github.com/ADB AI Agent"
        headers["X-Title"] = "ADB AI Agent"
    payload = {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 2048}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        raw_text = resp.text
        if resp.status_code == 429:
            send_log(task_id, "API_RATELIMIT", f"Provider: {name} | Model: {model}\nRaw: {raw_text[:600]}")
            return None
        if not resp.ok:
            send_log(task_id, "API_FAIL", f"Provider: {name} | Model: {model}\nStatus: {resp.status_code}\nRaw: {raw_text[:800]}")
            return None
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content
    except requests.exceptions.Timeout:
        send_log(task_id, "API_TIMEOUT", f"Provider: {name} | Model: {model}")
        return None
    except Exception as e:
        send_log(task_id, "API_EXCEPTION", f"Provider: {name} | Model: {model}\n{str(e)}")
        return None

def call_llm(messages: list, task_id: str) -> str:
    for url, key, model, name in PROVIDERS:
        send_log(task_id, "LLM_TRY", f"Provider: {name} | Model: {model}")
        ans = call_provider(messages, url, key, model, name, task_id)
        if ans:
            send_log(task_id, "LLM_OK", f"Provider: {name} | Model: {model}\n\nFull Response:\n{ans}")
            return ans
    send_log(task_id, "LLM_FATAL", "All providers and models exhausted.")
    return "<action>API_ERROR</action>"

def process_voice(file_path: str, task_id: str) -> str:
    if not GROQ_KEYS:
        return ""
    for key in GROQ_KEYS:
        try:
            with open(file_path, "rb") as f:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {key}"},
                    files={"file": f},
                    data={"model": AUDIO_MODEL},
                    timeout=20
                )
            if resp.status_code == 429:
                send_log(task_id, "VOICE_RATELIMIT", resp.text[:300])
                continue
            resp.raise_for_status()
            return resp.json().get("text", "").strip()
        except Exception as e:
            send_log(task_id, "VOICE_FAIL", str(e))
            continue
    return ""

def trim_history(history: list) -> list:
    if len(history) > 22:
        return history[:1] + history[-14:]
    return history

def return_to_telegram(chat_id: int, task_id: str):
    bot.send_message(chat_id, f"{tag(task_id)} 🔄 টেলিগ্রামে ফিরে আসছি...", parse_mode="HTML")
    run_adb("am", "start", "-n", "org.telegram.messenger/org.telegram.ui.LaunchActivity")
    time.sleep(1.5)

def send_confirm_buttons(chat_id: int, task_id: str):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Continue", callback_data=f"confirm_yes_{task_id}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"confirm_no_{task_id}")
    )
    bot.send_message(
        chat_id,
        f"{tag(task_id)} ⚠️ <b>এই প্ল্যানটি এক্সিকিউট করবো?</b>",
        parse_mode="HTML",
        reply_markup=markup
    )

def maybe_suggest_command(text: str) -> str:
    low = text.lower()
    if any(kw in low for kw in _ACTION_KEYWORDS):
        cmd = f"AC {text}"
        return f"\n\n💡 <b>এই কাজটি অটোমেট করতে চাইলে লিখুন:</b>\n<code>{html.escape(cmd)}</code>"
    return ""

def execute_actions(actions: list, ai_raw: str, chat_id: int, task_id: str) -> tuple[str, bool]:
    feedback = []
    task_done = False

    for action in actions:
        action = action.strip()
        if _cancel_event.is_set():
            break

        if action == "DONE":
            bot.send_message(chat_id, f"{tag(task_id)} ✅ টাস্ক সফলভাবে সম্পন্ন!", parse_mode="HTML")
            send_log(task_id, "TASK_DONE", "Completed successfully.")
            task_done = True
            return_to_telegram(chat_id, task_id)
            break

        if action == "REPLY":
            task_done = True
            break

        if action == "PLAN":
            continue

        if action == "API_ERROR":
            bot.send_message(chat_id, f"{tag(task_id)} ⚠️ সকল API ব্যর্থ হয়েছে।", parse_mode="HTML")
            task_done = True
            break

        base = action.split()[0] if action.split() else ""
        if base not in VALID_ACTIONS:
            feedback.append(f"System: Unauthorized action '{base}' blocked.")
            send_log(task_id, "BLOCKED", f"Unauthorized: {base}")
            continue

        bot.send_message(chat_id, f"{tag(task_id)} 🤖 <code>{html.escape(action)}</code>", parse_mode="HTML")
        send_log(task_id, "EXEC", action)

        if action.startswith("WRITE_CODE "):
            filename = os.path.basename(action.replace("WRITE_CODE ", "").strip())
            code_match = re.search(r'```[\w\-]*\s*\n(.*?)```', ai_raw, re.DOTALL)
            if code_match:
                os.makedirs(SAVE_DIR, exist_ok=True)
                filepath = os.path.join(SAVE_DIR, filename)
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(code_match.group(1).strip())
                    feedback.append(f"System: Code saved to {filepath}.")
                    bot.send_message(chat_id, f"{tag(task_id)} 💻 <b>কোড সেভ হয়েছে!</b>\n<code>{html.escape(filepath)}</code>", parse_mode="HTML")
                    send_log(task_id, "FILE_SAVED", filepath)
                except Exception as e:
                    feedback.append(f"System: File save error - {e}")
                    send_log(task_id, "FILE_ERROR", str(e))
            else:
                feedback.append("System: No code block found in response.")
            time.sleep(0.5)

        elif action.startswith("OPEN_APP "):
            app_name = action.replace("OPEN_APP ", "").strip().lower()
            pkg = next((v for k, v in APP_MAP.items() if k in app_name or app_name in k), None)
            if pkg:
                ok, _ = run_adb_action(chat_id, task_id, "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
                if not ok:
                    feedback.append("System: ADB error on OPEN_APP.")
                    break
                time.sleep(3.5)
                focus = get_current_app_focus()
                feedback.append(f"System: Opened {app_name}. Focus: {focus}. SCAN_SCREEN next.")
            else:
                feedback.append(f"System: '{app_name}' not in APP_MAP. Scan home screen manually.")

        elif action == "HOME":
            run_adb_action(chat_id, task_id, "input", "keyevent", "3")
            time.sleep(1.5)
            feedback.append(f"System: Home screen. Focus: {get_current_app_focus()}.")

        elif action == "BACK":
            run_adb_action(chat_id, task_id, "input", "keyevent", "4")
            time.sleep(1.0)
            feedback.append(f"System: Back pressed. Focus: {get_current_app_focus()}.")

        elif action == "SWIPE_UP":
            run_adb_action(chat_id, task_id, "input", "swipe", "500", "1800", "500", "400", "350")
            time.sleep(1.5)
            feedback.append("System: Swiped up. SCAN_SCREEN next.")

        elif action == "SWIPE_DOWN":
            run_adb_action(chat_id, task_id, "input", "swipe", "500", "400", "500", "1800", "350")
            time.sleep(1.5)
            feedback.append("System: Swiped down. SCAN_SCREEN next.")

        elif action == "SWIPE_RIGHT":
            run_adb_action(chat_id, task_id, "input", "swipe", "200", "900", "900", "900", "350")
            time.sleep(1.5)
            feedback.append("System: Swiped right. SCAN_SCREEN next.")

        elif action == "SCAN_SCREEN":
            data = scan_screen()
            send_log(task_id, "SCREEN_DUMP", data)
            if "ERROR" in data:
                feedback.append(f"System: Scan failed. {data}")
            else:
                feedback.append(f"System: Screen scanned.\n{data}")

        elif action.startswith("TAP "):
            parts = action.split()
            if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                tx, ty = int(parts[1]), int(parts[2])
                if 0 <= tx <= _screen_width and 0 <= ty <= _screen_height:
                    run_adb_action(chat_id, task_id, "input", "tap", str(tx), str(ty))
                    time.sleep(1.5)
                    feedback.append(f"System: Tapped ({tx},{ty}). Focus: {get_current_app_focus()}. SCAN_SCREEN next.")
                else:
                    feedback.append(f"System: Tap ({tx},{ty}) out of bounds. Blocked.")
                    send_log(task_id, "TAP_BLOCKED", f"{tx},{ty}")
            else:
                feedback.append("System: Invalid TAP format.")

        elif action.startswith("INPUT_TEXT "):
            text = action[len("INPUT_TEXT "):].strip()
            if not _SAFE_TEXT.match(text):
                feedback.append("System: Input rejected by safety filter.")
                send_log(task_id, "INPUT_BLOCKED", text)
                continue
            escaped = text.replace(' ', '%s').replace("'", "\\'")
            run_adb_action(chat_id, task_id, "input", "text", escaped)
            time.sleep(1.5)
            feedback.append(f"System: Typed '{text}'. SCAN_SCREEN or ENTER next.")

        elif action == "ENTER":
            run_adb_action(chat_id, task_id, "input", "keyevent", "66")
            time.sleep(2.0)
            feedback.append(f"System: Enter pressed. Focus: {get_current_app_focus()}. SCAN_SCREEN next.")

        elif action == "FLASHLIGHT_ON":
            run_adb_action(chat_id, task_id, "cmd", "flashlight", "on")
            feedback.append("System: Flashlight ON.")

        elif action == "FLASHLIGHT_OFF":
            run_adb_action(chat_id, task_id, "cmd", "flashlight", "off")
            feedback.append("System: Flashlight OFF.")

        elif action == "SCREENSHOT":
            bot.send_chat_action(chat_id, 'upload_photo')
            uid = uuid.uuid4().hex
            phone_path = f"/data/local/tmp/sc_{uid}.png"
            local_path = os.path.join(TEMP_DIR, f"sc_{uid}.png")
            run_adb("screencap", "-p", phone_path)
            subprocess.run(["adb", "pull", phone_path, local_path], capture_output=True, timeout=10)
            run_adb("rm", phone_path)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    bot.send_photo(chat_id, f, caption=f"📸 {tag(task_id)}", parse_mode="HTML")
                os.remove(local_path)
                feedback.append("System: Screenshot sent.")
                send_log(task_id, "SCREENSHOT", "Sent.")
            else:
                feedback.append("System: Screenshot pull failed.")
                send_log(task_id, "SCREENSHOT_FAIL", "adb pull failed.")

    return "\n".join(feedback), task_done


def run_task(chat_id: int, history: list, task_id: str):
    set_busy(True)
    _cancel_event.clear()
    bot.send_message(chat_id, f"{tag(task_id)} 🚀 এক্সিকিউশন শুরু...", parse_mode="HTML")
    send_log(task_id, "TASK_START", "Execution started.")
    try:
        for step_num in range(50):
            if _cancel_event.is_set():
                bot.send_message(chat_id, f"{tag(task_id)} 🛑 ক্যানসেল করা হয়েছে।", parse_mode="HTML")
                send_log(task_id, "TASK_CANCEL", f"Cancelled at step {step_num}.")
                break

            bot.send_chat_action(chat_id, 'typing')
            ai_raw = call_llm(history, task_id)

            think_m = re.search(r'<think>(.*?)</think>', ai_raw, re.DOTALL)
            if think_m:
                thinking = think_m.group(1).strip()
                bot.send_message(chat_id,
                    f"{tag(task_id)} 💭 <b>চিন্তা:</b>\n<blockquote>{safe_html(thinking)}</blockquote>",
                    parse_mode="HTML")
                send_log(task_id, "REASONING", thinking)

            actions = re.findall(r'<action>\s*(.*?)\s*</action>', ai_raw)
            if not actions:
                bot.send_message(chat_id, f"{tag(task_id)} ⚠️ কোনো action পাওয়া যায়নি।", parse_mode="HTML")
                send_log(task_id, "NO_ACTION", ai_raw[:600])
                break

            feedback, done = execute_actions([actions[0]], ai_raw, chat_id, task_id)

            if done or _cancel_event.is_set():
                break

            history.append({"role": "assistant", "content": ai_raw})
            history.append({"role": "user", "content": f"Execution Feedback:\n{feedback}"})
            history = trim_history(history)

    except Exception as e:
        bot.send_message(chat_id, f"{tag(task_id)} ⚠️ Error: {safe_html(str(e))}", parse_mode="HTML")
        send_log(task_id, "TASK_ERROR", str(e))
    finally:
        _active_task.pop(chat_id, None)
        set_busy(False)
        _cancel_event.clear()


def generate_plan(message, task_text: str, task_id: str):
    chat_id = message.chat.id
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User Request: {task_text}. Output <action>PLAN</action> with flowchart in <think> tags."}
    ]
    try:
        bot.send_chat_action(chat_id, 'typing')
        send_log(task_id, "PLAN_START", task_text)
        ai_raw = call_llm(history, task_id)

        think_m = re.search(r'<think>(.*?)</think>', ai_raw, re.DOTALL)
        if think_m:
            thinking = think_m.group(1).strip()
            bot.send_message(chat_id,
                f"{tag(task_id)} 💭 <b>প্ল্যান:</b>\n<blockquote>{safe_html(thinking)}</blockquote>",
                parse_mode="HTML")
            send_log(task_id, "PLAN_REASONING", thinking)

        if re.search(r'<action>\s*PLAN\s*</action>', ai_raw, re.IGNORECASE) or think_m:
            confirmed_history = history + [
                {"role": "assistant", "content": ai_raw},
                {"role": "user", "content": "System: Plan confirmed. Start Step 1. ONE action only. Do NOT output DONE until task is fully complete."}
            ]
            _active_task[chat_id] = {"history": confirmed_history, "task_id": task_id}
            send_confirm_buttons(chat_id, task_id)
        else:
            bot.send_message(chat_id, f"{tag(task_id)} ⚠️ প্ল্যান তৈরি ব্যর্থ হয়েছে।", parse_mode="HTML")
            send_log(task_id, "PLAN_FAIL", ai_raw[:500])
    except Exception as e:
        bot.send_message(chat_id, f"{tag(task_id)} ⚠️ Error: {safe_html(str(e))}", parse_mode="HTML")
        send_log(task_id, "PLAN_ERROR", str(e))
    finally:
        set_busy(False)


def handle_casual_chat(message, text: str, task_id: str):
    chat_id = message.chat.id
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User: {text}. Casual chat. Output <action>REPLY</action>."}
    ]
    try:
        bot.send_chat_action(chat_id, 'typing')
        ai_raw = call_llm(history, task_id)
        send_log(task_id, "CHAT_RESPONSE", ai_raw)

        display = re.sub(r'<think>.*?</think>', '', ai_raw, flags=re.DOTALL)
        display = re.sub(r'<action>\s*.*?\s*</action>', '', display, flags=re.DOTALL).strip()

        suggestion = maybe_suggest_command(text)
        final = (safe_html(display) if display else "") + suggestion
        if final.strip():
            bot.send_message(chat_id, final, parse_mode="HTML")
    finally:
        set_busy(False)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def handle_confirm(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized.")
        return

    chat_id = call.message.chat.id
    parts = call.data.split("_", 2)
    action_type = parts[1]
    task_id = parts[2] if len(parts) > 2 else "UNKNOWN"

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    if action_type == "yes":
        task_data = _active_task.get(chat_id)
        if not task_data or task_data.get("task_id") != task_id:
            bot.answer_callback_query(call.id, "Task expired.")
            return
        history = task_data["history"]
        _active_task.pop(chat_id, None)
        bot.answer_callback_query(call.id, "শুরু হচ্ছে...")
        send_log(task_id, "USER_CONFIRMED", "Continue pressed.")
        threading.Thread(target=run_task, args=(chat_id, history, task_id), daemon=True).start()

    elif action_type == "no":
        _active_task.pop(chat_id, None)
        bot.answer_callback_query(call.id, "ক্যানসেল।")
        bot.send_message(chat_id, f"{tag(task_id)} 🛑 ক্যানসেল করা হয়েছে।", parse_mode="HTML")
        send_log(task_id, "USER_CANCELLED", "Cancel pressed.")
        set_busy(False)


@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_authorized(message.from_user.id): return
    bot.reply_to(message, "🚀 ADB AI Agent অনলাইন!")

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    if not is_authorized(message.from_user.id): return
    chat_id = message.chat.id
    if is_busy():
        _cancel_event.set()
        bot.reply_to(message, "🛑 কাজ বন্ধ করা হচ্ছে...")
    elif chat_id in _active_task:
        task_id = _active_task[chat_id].get("task_id", "?")
        _active_task.pop(chat_id, None)
        bot.reply_to(message, f"{tag(task_id)} 🛑 প্ল্যান ক্যানসেল।", parse_mode="HTML")
        set_busy(False)
    else:
        bot.reply_to(message, "কিছু চলছে না।")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_authorized(message.from_user.id): return
    status = "⏳ ব্যস্ত" if is_busy() else "✅ ফ্রি"
    pending = "আছে" if message.chat.id in _active_task else "নেই"
    bot.reply_to(message,
        f"📈 <b>স্ট্যাটাস</b>\n"
        f"অবস্থা: <code>{status}</code>\n"
        f"Pending Plan: <code>{pending}</code>\n"
        f"Groq Keys: <code>{len(GROQ_KEYS)}</code>\n"
        f"Cerebras Keys: <code>{len(CEREBRAS_KEYS)}</code>\n"
        f"OpenRouter Keys: <code>{len(OPENROUTER_KEYS)}</code>",
        parse_mode="HTML"
    )

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not is_authorized(message.from_user.id): return
    if is_busy():
        bot.reply_to(message, "⏳ ব্যস্ত আছি।")
        return

    task_id = new_task_id()
    set_busy(True)
    _cancel_event.clear()
    uid = uuid.uuid4().hex
    voice_path = os.path.join(TEMP_DIR, f"voice_{uid}.ogg")

    try:
        bot.send_message(message.chat.id, "🎙️ প্রসেস করা হচ্ছে...")
        file_info = bot.get_file(message.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(voice_path, 'wb') as f:
            f.write(downloaded)

        text = process_voice(voice_path, task_id)
        if not text:
            bot.send_message(message.chat.id, "⚠️ বুঝতে পারিনি।")
            set_busy(False)
            return

        bot.send_message(message.chat.id, f"🗣️ <i>{html.escape(text)}</i>", parse_mode="HTML")

        if text.lower().startswith(("ac ", "cd ")):
            threading.Thread(target=generate_plan, args=(message, text[3:].strip(), task_id), daemon=True).start()
        else:
            threading.Thread(target=handle_casual_chat, args=(message, text, task_id), daemon=True).start()

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Voice error: {html.escape(str(e))}", parse_mode="HTML")
        send_log(task_id, "VOICE_ERROR", str(e))
        set_busy(False)
    finally:
        if os.path.exists(voice_path):
            os.remove(voice_path)

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if not is_authorized(message.from_user.id): return
    if not message.text or message.text.startswith('/'): return

    chat_id = message.chat.id
    text = message.text.strip()

    if is_busy():
        bot.reply_to(message, "⏳ ব্যস্ত আছি।")
        return

    task_id = new_task_id()
    set_busy(True)
    _cancel_event.clear()

    if text.upper().startswith(("AC ", "CD ")):
        threading.Thread(target=generate_plan, args=(message, text[3:].strip(), task_id), daemon=True).start()
    else:
        threading.Thread(target=handle_casual_chat, args=(message, text, task_id), daemon=True).start()


if __name__ == "__main__":
    device_model = connect_adb_on_startup()
    if device_model:
        status_msg = f"🟢 ADB AI Agent Online!\n✅ ADB Connected\nDevice: <code>{html.escape(device_model)}</code>"
    else:
        status_msg = "🟢 ADB AI Agent Online!\n⚠️ ADB Not Connected"

    print(f"✅ ADB AI Agent Active | Device: {device_model}")

    for uid in ALLOWED_USERS:
        try:
            bot.send_message(uid, status_msg, parse_mode="HTML")
        except Exception:
            pass

    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=20)
        except Exception as e:
            print(f"[POLLING ERROR]: {e}")
            time.sleep(5)