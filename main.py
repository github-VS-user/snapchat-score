from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import subprocess
import random
import json

app = FastAPI()

# --- 1. MEMORY GUARD (Fixes 'Session Not Created') ---
def kill_zombies():
    """Violently kills stuck processes to save RAM on startup."""
    subprocess.run(["pkill", "-f", "chrome"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "chromedriver"], stderr=subprocess.DEVNULL)

kill_zombies()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_REGISTRY = {}

# --- 2. THE CYBERPUNK STATUS PAGE ---
@app.get("/", response_class=HTMLResponse)
async def server_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SnapFarm Node | Online</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background: #050505; color: #00ff41; font-family: 'Courier New', monospace; margin: 0; display: flex; align-items: center; justify-content: center; height: 100vh; }
            .terminal { width: 80%; max-width: 600px; border: 1px solid #333; padding: 20px; background: #000; box-shadow: 0 0 20px rgba(0, 255, 65, 0.2); }
            h1 { border-bottom: 1px solid #333; padding-bottom: 10px; font-size: 18px; margin: 0 0 20px 0; text-transform: uppercase; letter-spacing: 2px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
            .stat-box { border: 1px solid #222; padding: 10px; }
            .label { font-size: 10px; color: #666; display: block; }
            .value { font-size: 24px; font-weight: bold; }
            .log-box { height: 150px; overflow: hidden; border-top: 1px dashed #333; padding-top: 10px; font-size: 12px; color: #888; }
            .blink { animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0; } }
            .status-ok { color: #00ff41; }
            .status-err { color: #ff0033; }
        </style>
    </head>
    <body>
        <div class="terminal">
            <h1>System_Node_v4 <span class="blink">_</span></h1>
            <div class="grid">
                <div class="stat-box">
                    <span class="label">ACTIVE INSTANCES</span>
                    <span class="value" id="bots">...</span>
                </div>
                <div class="stat-box">
                    <span class="label">MEMORY STATUS</span>
                    <span class="value status-ok">OPTIMIZED</span>
                </div>
            </div>
            <div class="log-box" id="logs">
                > Initializing UI...<br>
                > Connected to Railway Core...
            </div>
            <p style="font-size: 10px; color: #444; margin-top: 10px;">SPOOFING: WINDOWS 11 / CHROME 125</p>
        </div>
        <script>
            fetch('/bot/status').then(r => r.json()).then(data => {
                document.getElementById('bots').innerText = Object.keys(data).length;
            });
            // Fetch logs from the first active bot if available
            fetch('/bot/status').then(r => r.json()).then(data => {
                const user = Object.keys(data)[0];
                if(user) {
                    fetch('/bot/logs?username='+user).then(r => r.json()).then(d => {
                        document.getElementById('logs').innerHTML = d.logs.slice(-5).map(l => `> ${l}`).join('<br>');
                    });
                }
            });
        </script>
    </body>
    </html>
    """

def log(username, message):
    tag = "[Error]" if "fail" in str(message).lower() else "[System]"
    entry = f"{time.strftime('%H:%M:%S')} {tag} {message}"
    print(f"[{username}] {entry}")
    if username in BOT_REGISTRY:
        BOT_REGISTRY[username]["logs"].append(entry)
        if len(BOT_REGISTRY[username]["logs"]) > 50: BOT_REGISTRY[username]["logs"].pop(0)

class SnapBot:
    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.driver = None
        self.user_data = f"/app/driver_data/{username}"

    def spoof(self):
        """Injects fake Windows 11 parameters via CDP"""
        if not self.driver: return
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "platform": "Windows",
            "userAgentMetadata": {
                "brands": [{"brand": "Google Chrome", "version": "125"}, {"brand": "Chromium", "version": "125"}],
                "fullVersion": "125.0.6422.141",
                "platform": "Windows",
                "platformVersion": "15.0.0",
                "architecture": "x86",
                "mobile": False
            }
        })
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

    def start_driver(self):
        if self.driver: return
        
        options = uc.ChromeOptions()
        options.binary_location = "/usr/bin/chromium"
        
        # --- RAM SAVING FLAGS (Critical for 500MB Limit) ---
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--renderer-process-limit=1") # Limits Chrome to 1 process
        options.add_argument("--disable-extensions")
        options.add_argument("--blink-settings=imagesEnabled=true") 
        options.add_argument("--window-size=1366,768") # Smaller window = less RAM
        
        options.add_argument(f"--user-data-dir={self.user_data}")
        if self.proxy: options.add_argument(f'--proxy-server={self.proxy}')

        log(self.username, "Booting Memory-Optimized Chrome...")
        self.driver = uc.Chrome(options=options, driver_executable_path="/usr/bin/chromedriver")
        self.spoof()

    def login(self):
        try:
            self.start_driver()
            wait = WebDriverWait(self.driver, 20)
            log(self.username, "Opening Snapchat...")
            self.driver.get("https://web.snapchat.com/")
            time.sleep(5)

            if "browser not supported" in self.driver.page_source.lower():
                log(self.username, "CRITICAL: Browser Detected. Spoof Failed.")
                return "ERROR_DETECTED"

            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                return "LOGGED_IN"

            try:
                wait.until(EC.element_to_be_clickable((By.ID, "account_identifier"))).send_keys(self.username)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
                time.sleep(2)
                wait.until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(self.password)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            except: pass

            time.sleep(5)
            if "verification" in self.driver.page_source.lower(): return "2FA_REQUIRED"
            return "LOGGED_IN"
        except Exception as e:
            log(self.username, f"Crash: {str(e)[:40]}")
            return "ERROR"

    def farm(self):
        log(self.username, "Farming started.")
        while True: time.sleep(60)
    
    def stop(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None

@app.post("/bot/spawn")
async def spawn_bot(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    if user in BOT_REGISTRY:
        BOT_REGISTRY[user]["instance"].stop()
        del BOT_REGISTRY[user]
        time.sleep(2) # Wait for RAM release

    BOT_REGISTRY[user] = {"instance": SnapBot(user, data.get("password"), data.get("proxy")), "logs": [], "status": "Starting"}
    
    def run():
        status = BOT_REGISTRY[user]["instance"].login()
        BOT_REGISTRY[user]["status"] = status
        if status == "LOGGED_IN": BOT_REGISTRY[user]["instance"].farm()

    bg.add_task(run)
    return {"status": "Queued"}

@app.get("/bot/screenshot")
def get_screenshot(username: str):
    if os.path.exists(f"/tmp/{username}.png"): os.remove(f"/tmp/{username}.png")
    if username in BOT_REGISTRY and BOT_REGISTRY[username]["instance"].driver:
        fname = f"/tmp/{username}.png"
        BOT_REGISTRY[username]["instance"].driver.save_screenshot(fname)
        return FileResponse(fname, media_type="image/png")
    return JSONResponse({"error": "No bot"}, status_code=404)

@app.delete("/bot/remove")
def remove_bot(username: str):
    if username in BOT_REGISTRY:
        try: BOT_REGISTRY[username]["instance"].stop()
        except: pass
        del BOT_REGISTRY[username]
    return {"status": "Removed"}

@app.post("/bot/2fa")
async def handle_2fa(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    if user in BOT_REGISTRY:
        try:
            bot = BOT_REGISTRY[user]["instance"]
            bot.driver.find_element(By.TAG_NAME, "input").send_keys(data.get("code"))
            try: bot.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            except: pass
            time.sleep(5)
            if len(bot.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                 BOT_REGISTRY[user]["status"] = "Running"
                 bg.add_task(bot.farm)
                 return {"status": "Success"}
        except: pass
    return {"status": "Failed"}

@app.get("/bot/status")
def get_status(): return {k: v["status"] for k, v in BOT_REGISTRY.items()}

@app.get("/bot/logs")
def get_logs(username: str):
    if username in BOT_REGISTRY: return {"logs": BOT_REGISTRY[username]["logs"]}
    return {"logs": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
