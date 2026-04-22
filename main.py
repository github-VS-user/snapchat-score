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

# --- 1. FORCE CLEANUP ---
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

# --- 2. STATUS DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def server_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SnapFarm Node | Active</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background: #111; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .box { border: 2px solid #333; padding: 20px; width: 300px; background: #000; }
            .row { display: flex; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid #222; padding-bottom: 5px; }
            .green { color: #0f0; }
        </style>
    </head>
    <body>
        <div class="box">
            <div class="row"><span>SYSTEM</span> <span class="green">ONLINE</span></div>
            <div class="row"><span>BOTS</span> <span id="c">0</span></div>
            <div style="font-size: 10px; color: #666; margin-top: 10px;">DRIVER: NATIVE_MODE</div>
        </div>
        <script>
            fetch('/bot/status').then(r=>r.json()).then(d => document.getElementById('c').innerText = Object.keys(d).length);
        </script>
    </body>
    </html>
    """

def log(username, message):
    print(f"[{username}] {message}")
    if username in BOT_REGISTRY:
        BOT_REGISTRY[username]["logs"].append(f"{time.strftime('%H:%M')} {message}")
        if len(BOT_REGISTRY[username]["logs"]) > 50: BOT_REGISTRY[username]["logs"].pop(0)

class SnapBot:
    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.driver = None
        self.user_data = f"/app/driver_data/{username}"

    def start_driver(self):
        if self.driver: return
        
        options = uc.ChromeOptions()
        # CRITICAL: Point to the installed binary explicitly
        options.binary_location = "/usr/bin/chromium"
        
        # --- STABILITY FLAGS ---
        # These arguments are mandatory for Docker stability
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-popup-blocking")
        
        # Persistence
        options.add_argument(f"--user-data-dir={self.user_data}")
        
        if self.proxy: 
            options.add_argument(f'--proxy-server={self.proxy}')

        log(self.username, "Initializing Driver...")
        
        # --- THE FIX: Explicit Paths & disable patching ---
        try:
            self.driver = uc.Chrome(
                options=options,
                driver_executable_path="/usr/bin/chromedriver",
                browser_executable_path="/usr/bin/chromium",
                version_main=None, # Let it auto-detect
                headless=False,    # We handle headless via options above
                use_subprocess=True
            )
        except Exception as e:
            # Fallback: Sometimes version_main needs to be forced if auto-detect fails
            log(self.username, f"Auto-start failed ({str(e)}). Retrying with forced parameters...")
            self.driver = uc.Chrome(
                options=options,
                driver_executable_path="/usr/bin/chromedriver",
                version_main=120, 
                use_subprocess=True
            )

        self.driver.set_window_size(1280, 720)
        
        # Spoof Windows User Agent (Lightweight method)
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        })

    def login(self):
        try:
            self.start_driver()
            wait = WebDriverWait(self.driver, 20)
            
            log(self.username, "Navigating...")
            self.driver.get("https://web.snapchat.com/")
            time.sleep(5)
            
            # Detect Issues
            if "browser not supported" in self.driver.page_source.lower():
                return "ERROR_BROWSER_BLOCK"

            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                return "LOGGED_IN"

            # Login
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
            log(self.username, f"Error: {str(e)[:50]}")
            return "ERROR"

    def farm(self):
        log(self.username, "Farm Active.")
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

@app.post("/bot/stop")
def stop_bot(data: dict):
    user = data.get("username")
    if user in BOT_REGISTRY:
        BOT_REGISTRY[user]["instance"].stop()
        BOT_REGISTRY[user]["status"] = "Stopped"
    return {"status": "Stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
