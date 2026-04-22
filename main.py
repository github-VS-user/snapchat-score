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
import shutil

app = FastAPI()

# --- 1. MEMORY & PROCESS CLEANUP ---
def kill_zombies():
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

# --- 2. SERVER UI ---
@app.get("/", response_class=HTMLResponse)
async def server_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SnapFarm | System Node</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background: #0d0d0d; color: #e0e0e0; font-family: monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .panel { border: 1px solid #333; padding: 30px; width: 400px; background: #111; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            h1 { color: #FFFC00; margin: 0 0 20px; font-size: 20px; text-transform: uppercase; }
            .stat { display: flex; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid #222; padding-bottom: 5px; }
            .log-view { background: #000; height: 150px; overflow: hidden; font-size: 11px; color: #888; padding: 10px; margin-top: 20px; border: 1px solid #222; }
            .ok { color: #0f0; }
        </style>
    </head>
    <body>
        <div class="panel">
            <h1>System_Override_v6</h1>
            <div class="stat"><span>STATUS</span> <span class="ok">ONLINE</span></div>
            <div class="stat"><span>ACTIVE BOTS</span> <span id="count">...</span></div>
            <div class="stat"><span>DRIVER MODE</span> <span style="color: #FFFC00">MANUAL_VER_120</span></div>
            <div class="log-view" id="logs">Connecting...</div>
        </div>
        <script>
            const update = () => {
                fetch('/bot/status').then(r=>r.json()).then(d => {
                    document.getElementById('count').innerText = Object.keys(d).length;
                    if(Object.keys(d).length > 0) {
                        fetch('/bot/logs?username='+Object.keys(d)[0]).then(r=>r.json()).then(l => {
                            document.getElementById('logs').innerHTML = l.logs.slice(-7).join('<br>');
                        });
                    }
                });
            };
            setInterval(update, 3000); update();
        </script>
    </body>
    </html>
    """

def log(username, message):
    entry = f"{time.strftime('%H:%M:%S')} {message}"
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
        """Injects Windows 11 Identity"""
        if not self.driver: return
        try:
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
        except: pass

    def start_driver(self):
        if self.driver: return
        
        options = uc.ChromeOptions()
        options.binary_location = "/usr/bin/chromium"
        
        # STABILITY FLAGS
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--blink-settings=imagesEnabled=true")
        options.add_argument(f"--user-data-dir={self.user_data}")
        
        if self.proxy: options.add_argument(f'--proxy-server={self.proxy}')

        log(self.username, "Starting Driver (Version Check Skipped)...")
        
        # --- THE FIX: FORCE VERSION & SKIP PATCHING ---
        self.driver = uc.Chrome(
            options=options, 
            driver_executable_path="/usr/bin/chromedriver",
            version_main=125,  # Hardcodes version to skip auto-detection
            use_subprocess=True # Improves stability in Docker
        )
        self.driver.set_window_size(1366, 768)
        self.spoof()

    def login(self):
        try:
            self.start_driver()
            wait = WebDriverWait(self.driver, 25)
            
            log(self.username, "Navigating...")
            self.driver.get("https://web.snapchat.com/")
            
            # Check for bans/blocks immediately
            time.sleep(5)
            src = self.driver.page_source.lower()
            if "browser not supported" in src: return "ERROR_CAT_SCREEN"
            if "forbidden" in src: return "ERROR_IP_BAN"

            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                return "LOGGED_IN"

            log(self.username, "Inputting Creds...")
            try:
                wait.until(EC.element_to_be_clickable((By.ID, "account_identifier"))).send_keys(self.username)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
                time.sleep(2)
                wait.until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(self.password)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            except: pass

            time.sleep(8)
            if "verification" in self.driver.page_source.lower(): return "2FA_REQUIRED"
            return "LOGGED_IN"

        except Exception as e:
            log(self.username, f"Crash: {str(e)[:50]}")
            return "ERROR"

    def farm(self):
        log(self.username, "Farming Active.")
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
        time.sleep(2)

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
    if user in BOT_REGISTRY:
        try:
            bot = BOT_REGISTRY[user]["instance"]
            bot.driver.find_element(By.TAG_NAME, "input").send_keys(data.get("code"))
            bot.driver.find_element(By.XPATH, "//button[@type='submit']").click()
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

