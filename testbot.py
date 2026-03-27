import time
import os
import json
import requests
from cryptography.fernet import Fernet

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TOKEN")
WELCOME_MSG = "✅ البوت شغال الآن 🔥\nأي تحديث جديد على المودل رح يوصلك مباشرة"

print("🚀 بدء تشغيل البوت...")
print("TOKEN:", TOKEN)

if not TOKEN:
    raise Exception("❌ TOKEN مش موجود")

# ---------------- التشفير ----------------
secret = os.getenv("SECRET_KEY")
if not secret:
    raise Exception("❌ SECRET_KEY مش موجود")

cipher = Fernet(secret.encode())

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
        if not r.json().get("ok"):
            print("❌ Telegram error:", r.json())
    except Exception as e:
        print("❌ خطأ إرسال:", e)

def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        r = requests.get(url, params={"offset": offset}, timeout=10).json()
        return r if "result" in r else {"result":[]}
    except Exception as e:
        print("❌ Telegram error:", e)
        return {"result":[]}

# ---------------- FAKE SERVER (Render) ----------------
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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

for chat_id in users:
    send_message(chat_id, WELCOME_MSG)

last_update_id = None

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
                users[chat_id] = {"step": "username"}
                send_message(chat_id, "👤 ابعت رقمك الجامعي")

            elif chat_id in users:
                if users[chat_id]["step"] == "username":
                    users[chat_id]["username"] = text
                    users[chat_id]["step"] = "password"
                    send_message(chat_id, "🔑 ابعت كلمة السر")

                elif users[chat_id]["step"] == "password":
                    encrypted = cipher.encrypt(text.encode()).decode()
                    users[chat_id]["password"] = encrypted
                    users[chat_id]["step"] = "done"
                    save_users()
                    send_message(chat_id, "✅ تم التسجيل بنجاح 🔥")

                else:
                    send_message(chat_id, WELCOME_MSG)

            else:
                send_message(chat_id, "اكتب /start للبدء")

        time.sleep(2)

    except Exception as e:
        print("❌ خطأ عام:", e)
        time.sleep(5)
