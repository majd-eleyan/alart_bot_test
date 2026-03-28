import time
import os
import json
import requests
from cryptography.fernet import Fernet
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import re

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TOKEN")
WELCOME_MSG = "✅ بوت الاختبار شغال 🔥\nرح نفحص المودل التجريبي"
MOODLE_URL = "https://sandbox.moodledemo.net"

# ---------------- التشفير ----------------
key = os.getenv("SECRET_KEY").encode()
cipher = Fernet(key)

# ---------------- Users ----------------
users = {}

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f)

def load_users():
    global users
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except:
        users = {}

# ---------------- TELEGRAM ----------------
def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
        if not r.ok:
            print("❌ Telegram error:", r.text)
    except Exception as e:
        print("❌ إرسال:", e)

def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        r = requests.get(url, params={"offset": offset}, timeout=10)
        data = r.json()
        if not data.get("ok"):
            print("❌ Telegram error:", data)
            return {"result":[]}
        return data
    except Exception as e:
        print("❌ اتصال:", e)
        return {"result":[]}

# ---------------- MOODLE TEST ----------------
def fetch_moodle_updates(username, password):
    session = requests.Session()
    updates = []

    try:
        # تسجيل الدخول
        session.post(MOODLE_URL + "/login/index.php", data={
            "username": username,
            "password": password
        }, timeout=10)

        # Dashboard
        dash = session.get(MOODLE_URL + "/my/", timeout=10)

        if "login" in dash.url:
            print("❌ فشل تسجيل الدخول")
            return updates
        else:
            print("✅ تم تسجيل الدخول")

        # استخراج روابط الأنشطة
        links = re.findall(r'href="(https://[^"]+)"', dash.text)

        for link in links:
            if "course" in link or "mod" in link:
                updates.append(link)

        return list(set(updates))

    except Exception as e:
        print("❌ Moodle error:", e)
        return updates

# ---------------- SERVER ----------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()

# ---------------- MAIN ----------------
load_users()
print("✅ البوت شغال...")

last_update_id = None
last_check_time = 0

while True:
    try:
        updates = get_updates(last_update_id)

        for update in updates["result"]:
            last_update_id = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue

            chat_id = str(message["chat"]["id"])
            text = message.get("text", "")

            if text == "/start":
                users[chat_id] = {"step": "done"}
                save_users()
                send_message(chat_id, WELCOME_MSG)

            else:
                send_message(chat_id, "اكتب /start")

        # فحص المودل كل دقيقة
        if time.time() - last_check_time > 60:
            last_check_time = time.time()

            for chat_id in users:
                new_updates = fetch_moodle_updates("student", "moodle")

                print("📊 updates:", new_updates)
                send_message(chat_id, f"📊 عدد العناصر: {len(new_updates)}")

        time.sleep(2)

    except Exception as e:
        print("❌ خطأ عام:", e)
        time.sleep(5)
