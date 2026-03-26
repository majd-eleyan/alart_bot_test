import time
import os
import json
import requests
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TOKEN")
WELCOME_MSG = "✅ البوت شغال الآن 🔥\nأي تحديث جديد على المودل رح يوصلك مباشرة"
MOODLE_URL = "https://sandbox.moodledemo.net"

# ---------------- التشفير ----------------
# لو ما عندك مفتاح جديد تولد:
# key = Fernet.generate_key()
# with open("secret.key","wb") as f: f.write(key)

key = os.getenv("SECRET_KEY").encode()
cipher = Fernet(key)

# ---------------- Users dict ----------------
users = {}

# ----------- SAVE / LOAD USERS -----------
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

# ------------- TELEGRAM ----------------
def send_message(chat_id, text):
    for i in range(3):  # retry
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
            return
        except Exception as e:
            print("❌ إعادة محاولة إرسال:", e)
            time.sleep(2)
def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        return requests.get(url, params={"offset": offset}, timeout=10).json()
    except Exception as e:
        print("❌ Telegram error:", e)
        return {"result":[]}

# ------------- SELENIUM ----------------
from selenium.webdriver.firefox.service import Service

def init_driver():
    options = Options()
    options.add_argument("--headless")

    service = Service("/data/data/com.termux/files/usr/bin/geckodriver")

    driver = webdriver.Firefox(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver

def fetch_moodle_updates(username, password):
    driver = init_driver()
    updates = []
    try:
        driver.get(MOODLE_URL + "/login/index.php")
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)

        # تحقق من تسجيل الدخول
        if "login" in driver.current_url:
            print("❌ فشل تسجيل الدخول")
            driver.quit()
            return updates
        else:
            print("✅ تم تسجيل الدخول بنجاح")

        # Dashboard: استخراج جميع المساقات
        courses = driver.find_elements(By.CSS_SELECTOR, ".coursebox a, .card a")
        for course in courses:
            try:
                title = course.text.split("\n")[0]
                link = course.get_attribute("href")
                driver.get(link)
                time.sleep(2)

                # استخراج الأقسام
                sections = driver.find_elements(By.CSS_SELECTOR, "li[id^='section-']")
                for sec in sections:
                    # فتح Toggle إذا موجود
                    try:
                        toggle = sec.find_element(By.CSS_SELECTOR, ".sectionname")
                        toggle.click()
                        time.sleep(0.5)
                    except: pass

                    activities = sec.find_elements(By.CSS_SELECTOR, ".activity a")
                    for act in activities:
                        text = act.text.strip()
                        href = act.get_attribute("href")
                        if len(text) > 0:
                            updates.append(f"{title} - {text} - {href}")
            except: continue

        driver.quit()
        return updates

    except Exception as e:
        print("❌ Moodle error:", e)
        driver.quit()
        return updates

# ------------- MAIN LOOP ----------------
load_users()
print("✅ البوت شغال...")

for chat_id in users:
    send_message(chat_id, WELCOME_MSG)

last_update_id = None
last_check_time = 0
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# ---------- FAKE SERVER ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

# ---------- RUN BOT + SERVER ----------
threading.Thread(target=run_server).start()
while True:
    try:
        updates = get_updates(last_update_id)
        for update in updates["result"]:
            last_update_id = update["update_id"] + 1
            message = update.get("message")
            if not message: continue
            chat_id = str(message["chat"]["id"])
            text = message.get("text", "")

            if text == "/start":
                users[chat_id] = {"step":"username"}
                send_message(chat_id,"👤 ابعت رقمك الجامعي")
            elif chat_id in users:
                if users[chat_id]["step"] == "username":
                    users[chat_id]["username"] = text
                    users[chat_id]["step"] = "password"
                    send_message(chat_id,"🔑 ابعت كلمة السر")
                elif users[chat_id]["step"] == "password":
                    encrypted = cipher.encrypt(text.encode()).decode()
                    users[chat_id]["password"] = encrypted
                    users[chat_id]["step"] = "done"
                    users[chat_id]["last_seen"] = []
                    save_users()
                    send_message(chat_id,"✅ تم التسجيل بنجاح 🔥")
                else:
                    send_message(chat_id, WELCOME_MSG)
            else:
                send_message(chat_id,"اكتب /start للبدء")

        # Moodle check كل دقيقة
        if time.time() - last_check_time > 60:
            last_check_time = time.time()
            for chat_id, data in users.items():
                if data.get("step") != "done": continue
                username = data["username"]
                password = cipher.decrypt(data["password"].encode()).decode()
                new_updates = fetch_moodle_updates(username, password)

                print("📊 updates:", new_updates)

                send_message(chat_id, f"📊 عدد العناصر: {len(new_updates)}")
                diff = [u for u in new_updates if u not in data.get("last_seen",[])]
                for item in diff:
                    send_message(chat_id,f"📢 تحديث جديد:\n{item}")
                if diff:
                    users[chat_id]["last_seen"].extend(diff)
                    save_users()

        time.sleep(1)
    except Exception as e:
        print("❌ خطأ عام:", e)
        time.sleep(3)
