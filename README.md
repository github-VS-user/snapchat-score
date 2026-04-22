# 👻 SnapFarm AI - Multi-Bot Command Center

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95-009688?logo=fastapi&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.0-43B02A?logo=selenium&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)

**SnapFarm AI** is a production-grade automation suite for managing multiple Snapchat accounts simultaneously. It features a **Headless "Undetected" Browser Engine** hosted on Railway, controlled via a modern **React Dashboard** (V0/Vercel).

> **⚠️ Disclaimer:** This tool is for educational purposes only. Automating Snapchat accounts violates their Terms of Service and may result in account bans. Use at your own risk.

---

## 🚀 Key Features

*   **Multi-Bot Architecture**: Run 10+ accounts simultaneously (dependent on server RAM).
*   **Windows 10 Spoofing**: Bypasses "Browser Not Supported" and "Automated Software" detection.
*   **Visual Debugging**: View real-time screenshots of the bot's browser to solve Captchas or check status.
*   **Remote 2FA Handling**: Input 2FA codes directly from the Web Dashboard—no need to access the server.
*   **Session Persistence**: Docker Volumes keep your bots logged in even after server restarts.
*   **Proxy Support**: Route each bot through a unique IP (`ip:port`) to prevent chain bans.

---

## 🛠️ Architecture

The system consists of two parts:

1.  **The Engine (Backend):** A Python FastAPI server running on **Railway**. It manages the Dockerized Chrome instances using `undetected-chromedriver`.
2.  **The Dashboard (Frontend):** A React UI running on **Vercel** (generated via V0). It communicates with the Engine via REST API.

---

## 📦 Deployment Guide

### Phase 1: The Backend (Railway)

1.  **Fork/Clone this Repository.**
2.  **Create a Project on Railway:**
    *   Go to [Railway.app](https://railway.app) and click "New Project" > "Deploy from GitHub".
    *   Select this repository.
3.  **Configure the Volume (CRITICAL):**
    *   Once deployed, click on your service card.
    *   Go to the **Volumes** tab.
    *   Click **Add Volume**.
    *   **Mount Path:** `/app/driver_data`
    *   *Note: Without this, you will have to log in again every time you update the code.*
4.  **Get Your URL:**
    *   Go to the **Settings** tab > **Networking**.
    *   Copy the **Public Domain** (e.g., `https://your-project.up.railway.app`).

### Phase 2: The Frontend (V0/Vercel)

1.  Go to [v0.dev](https://v0.dev).
2.  Paste the "Dashboard Prompt" (found in `docs/v0_prompt.txt` or described below).
3.  **Hardcode your Railway URL** into the V0 configuration prompt:
    > "Set the API Base URL to: https://your-project.up.railway.app"
4.  **Deploy to Vercel** via the V0 interface.

---

##  Configuration

### Environment Variables (Railway)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | The port FastAPI listens on (Railway sets this automatically). |

---

##  API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/bot/spawn` | Starts a new Chrome instance. Requires JSON `{user, pass, proxy}`. |
| `GET` | `/bot/status` | Returns the state of all bots (Running, Stopped, 2FA_REQUIRED). |
| `GET` | `/bot/screenshot` | Returns a PNG snapshot of the bot's current view. Query: `?username=xyz`. |
| `POST` | `/bot/2fa` | Submits the verification code. JSON `{username, code}`. |
| `GET` | `/bot/logs` | Fetches the last 150 lines of terminal output for a specific bot. |
| `DELETE`| `/bot/remove` | Stops the bot and removes it from memory. |

---

##  Troubleshooting

### "Browser Not Supported" Screen
*   **Cause:** Snapchat detected the Linux Headless environment.
*   **Fix:** Ensure `main.py` includes the User-Agent spoofing line:
    ```python
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")
    ```
*   **Action:** Delete the bot from the dashboard and re-add it to clear the cache.

