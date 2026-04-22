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

# --- 0. MEMORY & ZOMBIE CLEANUP (Essential for 500MB limit) ---
def kill_zombies():
    print("🧹 System: Purging zombie Chrome processes...")
    subprocess.run(["pkill", "-f", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

kill_zombies()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_REGISTRY = {}

def log(username, message):
    timestamp = time.strftime("%H:%M:%S")
    tag = "[Error]" if "fail" in str(message).lower() else "[System]"
    entry = f"{timestamp} {tag} {message}"
    print(f"[{username}] {entry}")
    if username in BOT_REGISTRY:
        BOT_REGISTRY[username]["logs"].append(entry)
        if len(BOT_REGISTRY[username]["logs"]) > 50:
            BOT_REGISTRY[username]["logs"].pop(0)

# --- THE SERVER STATUS PAGE (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def server_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SnapFarm Node | Online</title>
        <style>
            :root { --neon: #FFFC00; --bg: #0a0a0a; --panel: #111; --text: #eee; }
            body { background: var(--bg); color: var(--text); font-family: 'Courier New', monospace; margin: 0; display: flex; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }
            .container { width: 90%; max-width: 600px; border: 1px solid #333; padding: 2rem; background: var(--panel); box-shadow: 0 0 20px rgba(0,0,0,0.5); position: relative; }
            .container::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: var(--neon); box-shadow: 0 0 10px var(--neon); }
            h1 { margin: 0 0 1rem; font-size: 1.5rem; text-transform: uppercase; letter-spacing: 2px; color: var(--neon); }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
            .card { background: #1a1a1a; padding: 1rem; border: 1px solid #333; }
            .label { font-size: 0.8rem; color: #888; display: block; margin-bottom: 0.5rem; }
            .value { font-size: 1.5rem; font-weight: bold; }
            .status-dot { display: inline-block; width: 10px; height: 10px; background: #0f0; border-radius: 50%; box-shadow: 0 0 10px #0f0; margin-right: 10px; }
            .log-window { background: #000; border: 1px solid #333; height: 150px; overflow-y: auto; padding: 10px; font-size: 0.8rem; color: #aaa; }
            .log-entry { margin-bottom: 4px; border-bottom: 1px solid #111; padding-bottom: 2px; }
            .blink { animation: blinker 1.5s linear infinite; }
            @keyframes blinker { 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1><span class="status-dot"></span>SnapFarm Node</h1>
            <div class="grid">
                <div class="card">
                    <span class="label">ACTIVE BOTS</span>
                    <span class="value" id="bot-count">0</span>
                </div>
                <div class="card">
                    <span class="label">SERVER STATUS</span>
                    <span class="value" style="color: #0f0;">OPERATIONAL</span>
                </div>
            </div>
            <div class="card">
                <span class="label">LATEST SYSTEM LOGS</span>
                <div class="log-window" id="console">
                    <div class="log-entry">> System initialized...</div>
                    <div class="log-entry">> Waiting for V0 command...</div>
                </div>
            </div>
            <p style="margin-top: 1rem; font-size: 0.8rem; text-align: center; color: #666;">
                MEMORY GUARD: <span style="color: var(--neon)">ACTIVE</span> | SPOOFING: <span style="color: var(--neon)">WINDOWS 11</span>
            </p>
        </div>
        <script>
            async function updateStats() {
                try {
                    // Fetch Bot Status
                    const statusRes = await fetch('/bot/status');
                    const statusData = await statusRes.json();
                    document.getElementById('bot-count').innerText = Object.keys(statusData).length;

                    // Fetch Logs (from first available bot)
                    const users = Object.keys(statusData);
                    if (users.length > 0) {
                        const logsRes = await fetch(`/bot/logs?username=${users[0]}`);
                        const logsData = await logsRes.json();
                        const consoleDiv = document.getElementById('console');
                        if(logsData.logs.length > 0) {
                            consoleDiv.innerHTML = logsData.logs.map(l => `<div class="log-entry">${l}</div>`).reverse().join('');
                        }
                    }
                } catch (e) {
                    console.log("Polling error", e);
                }
            }
            setInterval(updateStats, 3000); // Update every 3 seconds
            updateStats();
        </script>
    </body>
    </html>
    """

# --- THE BOT ENGINE (With Windows Spoofing) ---
class SnapBot:
    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.driver = None
        self.user_data = f"/app/driver_data/{username}"

    def spoof_fingerprint(self):
        """Injects Windows 11 identity into the browser core"""
        if not self.driver: return
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "platform": "Windows",
            "userAgentMetadata": {
                "brands": [{"brand": "Google Chrome", "version": "124"}, {"brand": "Chromium", "version": "124"}],
                "fullVersion": "124.0.6367.119",
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
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"--user-data-dir={self.user_data}")
        
        # Fallback UA
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        log(self.username, "Starting Chrome (Deep Spoof Active)...")
        self.driver = uc.Chrome(options=options, driver_executable_path="/usr/bin/chromedriver")
        self.spoof_fingerprint()

    def login(self):
        try:
            self.start_driver()
            wait = WebDriverWait(self.driver, 15)
            
            log(self.username, "Opening Snapchat...")
            self.driver.get("https://web.snapchat.com/")
            time.sleep(5)
            
            # Check for the block screen
            if "browser not supported" in self.driver.page_source.lower():
                log(self.username, "CRITICAL: Spoof failed. Browser detected.")
                return "ERROR_DETECTED"

            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                return "LOGGED_IN"

            # Login Logic
            try:
                wait.until(EC.element_to_be_clickable((By.ID, "account_identifier"))).send_keys(self.username)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
                time.sleep(2)
                wait.until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(self.password)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            except:
                pass

            time.sleep(5)
            if "verification" in self.driver.page_source.lower():
                return "2FA_REQUIRED"
            
            return "LOGGED_IN"

        except Exception as e:
            log(self.username, f"Error: {str(e)[:50]}")
            return "ERROR"

    def farm(self):
        log(self.username, "Farming active.")
        while True:
            time.sleep(60)
    
    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

# --- API ENDPOINTS ---
@app.post("/bot/spawn")
async def spawn_bot(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    # RAM Protection: Kill old instance first
    if user in BOT_REGISTRY:
        BOT_REGISTRY[user]["instance"].stop()
        del BOT_REGISTRY[user]

    BOT_REGISTRY[user] = {"instance": SnapBot(user, data.get("password"), data.get("proxy")), "logs": [], "status": "Starting"}
    
    def run():
        status = BOT_REGISTRY[user]["instance"].login()
        BOT_REGISTRY[user]["status"] = status
        if status == "LOGGED_IN":
             BOT_REGISTRY[user]["instance"].farm()

    bg.add_task(run)
    return {"status": "Queued"}

@app.get("/bot/screenshot")
def get_screenshot(username: str):
    if os.path.exists(f"/tmp/{username}.png"):
        os.remove(f"/tmp/{username}.png")
        
    if username in BOT_REGISTRY and BOT_REGISTRY[username]["instance"].driver:
        fname = f"/tmp/{username}.png"
        BOT_REGISTRY[username]["instance"].driver.save_screenshot(fname)
        return FileResponse(fname, media_type="image/png")
    return JSONResponse({"error": "No bot"}, status_code=404)

@app.delete("/bot/remove")
def remove_bot(username: str):
    if username in BOT_REGISTRY:
        try:
            BOT_REGISTRY[username]["instance"].stop()
        except:
            pass
        del BOT_REGISTRY[username]
    return {"status": "Removed"}

@app.post("/bot/stop")
def stop_bot(data: dict):
    user = data.get("username")
    if user in BOT_REGISTRY:
        BOT_REGISTRY[user]["instance"].stop()
        BOT_REGISTRY[user]["status"] = "Stopped"
    return {"status": "Stopped"}

@app.post("/bot/2fa")
async def handle_2fa(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    code = data.get("code")
    if user in BOT_REGISTRY:
        bot = BOT_REGISTRY[user]["instance"]
        try:
            bot.driver.find_element(By.TAG_NAME, "input").send_keys(code)
            try:
                bot.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            except:
                pass
            time.sleep(5)
            if len(bot.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                 BOT_REGISTRY[user]["status"] = "Running"
                 bg.add_task(bot.farm)
                 return {"status": "Success"}
        except:
            pass
    return {"status": "Failed"}

@app.get("/bot/status")
def get_status():
    return {k: v["status"] for k, v in BOT_REGISTRY.items()}

@app.get("/bot/logs")
def get_logs(username: str):
    if username in BOT_REGISTRY:
        return {"logs": BOT_REGISTRY[username]["logs"]}
    return {"logs": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
