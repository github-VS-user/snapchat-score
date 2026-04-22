from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import random

app = FastAPI()

# --- Config & Security ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Registry
BOT_REGISTRY = {}

# --- Logging System ---
def log(username, message):
    timestamp = time.strftime("%H:%M:%S")
    msg_str = str(message)
    tag = "[Error]" if "Exception" in msg_str or "fail" in msg_str.lower() else "[System]"
    
    entry = f"{timestamp} {tag} {msg_str}"
    print(f"[{username}] {entry}") # Print to Railway Logs
    
    if username in BOT_REGISTRY:
        BOT_REGISTRY[username]["logs"].append(entry)
        if len(BOT_REGISTRY[username]["logs"]) > 150:
            BOT_REGISTRY[username]["logs"].pop(0)

# --- The Bot Engine ---
class SnapBot:
    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.driver = None
        self.running = False
        self.user_data = f"/app/driver_data/{username}"

    def start_driver(self):
        if self.driver: return
        
        options = uc.ChromeOptions()
        options.binary_location = "/usr/bin/chromium"
        
        # --- THE FIX FOR "BROWSER NOT SUPPORTED" ---
        # 1. Spoof Windows 10 User Agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        
        # 2. Railway/Docker Flags
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # 3. Persistence
        options.add_argument(f"--user-data-dir={self.user_data}")

        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        log(self.username, "Booting Chrome (Windows 10 Spoof)...")
        self.driver = uc.Chrome(options=options, driver_executable_path="/usr/bin/chromedriver")

    def login(self):
        try:
            self.start_driver()
            wait = WebDriverWait(self.driver, 20)
            
            log(self.username, "Opening Snapchat...")
            self.driver.get("https://web.snapchat.com/")
            time.sleep(5)

            # Check if already logged in
            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                log(self.username, "Session restored! No login needed.")
                return "LOGGED_IN"

            log(self.username, "Entering credentials...")
            
            # Login Flow
            wait.until(EC.element_to_be_clickable((By.ID, "account_identifier"))).send_keys(self.username)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            time.sleep(2)
            wait.until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            log(self.username, "Credentials sent. Waiting...")
            time.sleep(8)
            
            # Check for 2FA or Success
            if "verification" in self.driver.page_source.lower():
                log(self.username, "ALERT: 2FA Code Required.")
                return "2FA_REQUIRED"
            
            if len(self.driver.find_elements(By.CLASS_NAME, "FiLwP")) > 0:
                return "LOGGED_IN"
            
            return "UNKNOWN"

        except Exception as e:
            log(self.username, f"Login Error: {str(e)}")
            return "ERROR"

    def farm(self):
        """Your Farming Logic (From the code you pasted)"""
        self.running = True
        log(self.username, "Farming Engine Started.")
        
        wait = WebDriverWait(self.driver, 10)
        
        # Paths
        friends_path = By.CLASS_NAME, "FiLwP"
        snap_btn = By.CLASS_NAME, "HEkDJ"
        take_snap = By.CLASS_NAME, "UEYhD"
        send_btn = By.XPATH, "//button[contains(., 'Send')]"

        while self.running:
            try:
                log(self.username, "Starting new cycle...")
                
                # 1. Click Friend
                friends = wait.until(EC.presence_of_all_elements_located(friends_path))
                if not friends: continue
                
                # Pick a random friend (skipping 'My AI' usually at top)
                target = friends[1] if len(friends) > 1 else friends[0]
                target.click()
                time.sleep(random.uniform(1, 2))
                
                # 2. Open Camera
                wait.until(EC.element_to_be_clickable(snap_btn)).click()
                time.sleep(random.uniform(1, 2))
                
                # 3. Take Snap
                options = wait.until(EC.presence_of_all_elements_located(take_snap))
                random.choice(options).click()
                time.sleep(2)
                
                # 4. Select Recipients (Just the current friend for safety)
                # Note: Your old code selected EVERYONE. That causes bans.
                # We select just the open chat for now to be safe.
                wait.until(EC.element_to_be_clickable(send_btn)).click()
                
                log(self.username, "Snap Sent! Resting...")
                time.sleep(random.uniform(30, 60))

            except Exception as e:
                log(self.username, f"Cycle Error: {e}. Refreshing...")
                try:
                    self.driver.refresh()
                    time.sleep(10)
                except:
                    pass
    
    def stop(self):
        self.running = False
        if self.driver:
            self.driver.quit()
            self.driver = None

# --- API Endpoints ---

@app.post("/bot/spawn")
async def spawn_bot(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    pw = data.get("password")
    proxy = data.get("proxy")
    
    if user in BOT_REGISTRY:
        return {"status": "Exists", "message": "Bot already exists"}

    BOT_REGISTRY[user] = {
        "instance": SnapBot(user, pw, proxy), 
        "logs": [], 
        "status": "Starting"
    }
    
    bot = BOT_REGISTRY[user]["instance"]
    
    def run_sequence():
        status = bot.login()
        BOT_REGISTRY[user]["status"] = status
        if status == "LOGGED_IN":
            BOT_REGISTRY[user]["status"] = "Running"
            bot.farm()
            
    bg.add_task(run_sequence)
    return {"status": "Initiated"}

@app.post("/bot/2fa")
async def handle_2fa(data: dict, bg: BackgroundTasks):
    user = data.get("username")
    code = data.get("code")
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

@app.get("/bot/screenshot")
def get_screenshot(username: str):
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
    return {"status": "Removed", "remaining_bots": list(BOT_REGISTRY.keys())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
