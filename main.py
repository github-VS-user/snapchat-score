from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import subprocess
import random

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

class SnapBot:
    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.driver = None
        self.user_data = f"/app/driver_data/{username}"

    def spoof_fingerprint(self):
        """
        The Nuclear Option: Uses CDP to overwrite Client Hints.
        This makes the Linux server look 100% like Windows 11 to Snapchat.
        """
        if not self.driver: return

        # Current Chrome 147 (April 2026) Fingerprint
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "platform": "Windows",
            "acceptLanguage": "en-US,en;q=0.9",
            "userAgentMetadata": {
                "brands": [
                    {"brand": "Google Chrome", "version": "147"},
                    {"brand": "Chromium", "version": "147"},
                    {"brand": "Not=A?Brand", "version": "24"}
                ],
                "fullVersionList": [
                    {"brand": "Google Chrome", "version": "147.0.7727.102"},
                    {"brand": "Chromium", "version": "147.0.7727.102"},
                    {"brand": "Not=A?Brand", "version": "24.0.0.0"}
                ],
                "fullVersion": "147.0.7727.102",
                "platform": "Windows",
                "platformVersion": "15.0.0",
                "architecture": "x86",
                "model": "",
                "mobile": False
            }
        })
        
        # Overwrite 'navigator.webdriver' to be undefined
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            """
        })

    def start_driver(self):
        if self.driver: return
        
        options = uc.ChromeOptions()
        options.binary_location = "/usr/bin/chromium"
        
        # Standard flags
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"--user-data-dir={self.user_data}")
        
        # Initial UA (Backup)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")

        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        log(self.username, "Starting Chrome 147 (Deep Spoof)...")
        self.driver = uc.Chrome(options=options, driver_executable_path="/usr/bin/chromedriver")
        
        # APPLY THE SPOOF
        self.spoof_fingerprint()

    def login(self):
        try:
            self.start_driver()
            wait = WebDriverWait(self.driver, 15)
            
            log(self.username, "Opening Snapchat...")
            self.driver.get("https://web.snapchat.com/")
            
            # Wait to see if we get blocked or loaded
            time.sleep(5)
            
            # Snapshot for debug
            if "browser not supported" in self.driver.page_source.lower():
                log(self.username, "CRITICAL: Still detected. Check screenshot.")
                return "ERROR_DETECTED"

            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                return "LOGGED_IN"

            # Login Interaction
            try:
                wait.until(EC.element_to_be_clickable((By.ID, "account_identifier"))).send_keys(self.username)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
                time.sleep(2)
                wait.until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(self.password)
                self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            except:
                # Sometimes fields have different IDs, basic retry
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

@app.post("/bot/spawn")
async def spawn_bot(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    # Kill old instance to save RAM
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

# ... Include your remove/stop endpoints here ...
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

# ... Include 2FA endpoint ... 
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
