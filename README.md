# KNWLDGBox - OSINT & Tools Platform

KNWLDGBox is a platform for Open Source Intelligence (OSINT) and Media Tools. It provides a modular web interface to manage data leaks, social forensics, network graphs, media downloading, image forensics, and more.

The project is split into two parts:
- **Backend**: A FastAPI Python server handling background tasks, WebSockets, APIs, and external tool integrations (like `yt-dlp`, `holehe`, `sherlock`, etc.).
- **Frontend**: A Vue.js application using Vite for a fast and reactive user experience.

---

## Prerequisites

Depending on how you plan to run KNWLDGBox, you will need different prerequisites.

### 🐳 For Docker Users (Recommended)
You only need to install Docker:
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose.

*(Note: The Docker container automatically includes Node.js, Python, Git, and Chromium, so you do **not** need to install them on your host machine!)*

### 💻 For Local Development
If you prefer to run the app manually without Docker, make sure you have the following installed:
- **Python 3.10+** (with `venv` support) for the backend.
- [Node.js](https://nodejs.org/) (v16+ recommended) and `npm` for the frontend.
- [Git](https://git-scm.com/)
- **Chromium Browser** (Required for the Local Archives module to generate screenshots and PDFs). On Ubuntu/Debian, install it via: `sudo apt install chromium`

---

## 🛠️ Installation Guide

### 1. Backend Setup (Python)

We highly recommend using a virtual environment to keep your Python dependencies isolated.

1. **Create and activate a new virtual environment (`venv`)**:
   ```bash
   python3 -m venv knwldg
   source knwldg/bin/activate  # On Windows use: knwldg\Scripts\activate
   ```

2. **Navigate to the backend directory and install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy the example environment file and fill in your API keys (Shodan, VirusTotal, Telegram API, etc.).
   ```bash
   cp example.env .env
   ```
   
   *(Note: You can configure API keys directly through the "Settings" tab in the web interface later. See the Tutorials section below for guides on getting specific API keys.). And use example.env or .env.example in copy.*

### 2. Frontend Setup (Vue.js)

1. **Open a new terminal window** (or keep the same if you prefer to run things sequentially) and navigate to the frontend directory:
   ```bash
   cd app
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

---

## 🚀 How to Launch the Application

We have provided two convenient scripts depending on how you want to run the application.

<details>
<summary><b>💻 Local Development Mode</b> (Click to expand)</summary>

Use this method if you are running the app on your local computer for development or personal use.

Simply run this command from the root of the project:
```bash
./start.sh
```

- The script automatically activates the `knwldg` virtual environment and executes the backend.
- The frontend will start in development mode (`npm run dev`).
- To stop both servers, simply press `Ctrl+C` in your terminal.

*(Alternatively, you can manually start the backend in one terminal with `uvicorn main:app --reload` and the frontend in another terminal with `npm run dev`).*
</details>

<details>
<summary><b>🌍 Home Server / Production Mode (Docker)</b> (Click to expand)</summary>

Use this method if you are hosting the app on a home server (e.g., accessed via Tailscale or LAN).

This approach uses Docker and Docker Compose to containerize the entire application into a single production-ready image. Persistent data (API keys, media, and investigation graphs) is securely saved on your host machine so it survives restarts.

Simply run this command from the root of the project:
```bash
docker compose up --build -d
```

- The application will be automatically built and started in the background on **port 8000** (e.g., `http://localhost:8000`).
- All your configurations, OSINT reports, and data will be safely saved in `data/app/` in your project folder.
- Downloaded media will be directly available in your host machine at `~/Downloads/KNWLDGBox/`.
- You can check the logs anytime with `docker compose logs -f`.
- To stop the application, run `docker compose down`.
</details>

---

## 📚 Tutorials & Setup Guides

Here are quick guides for setting up external APIs used by KNWLDGBox.

<details>
<summary><b>🤖 How to Setup OpenRouter AI Summaries</b> (Click to expand)</summary>

KNWLDGBox allows you to summarize all your active RSS feeds and Telegram channels at once using LLMs via OpenRouter.

1. **Get an API Key**:
   - Go to [OpenRouter.ai](https://openrouter.ai/) and create a free account.
   - Generate a new API Key in your account settings.

2. **Configure KNWLDGBox**:
   - Open your KNWLDGBox web interface.
   - Navigate to the **Settings** tab (the gear icon).
   - Under the **OSINT APIs** section, paste your API key into the `OpenRouter API Key` field.
   - Select your preferred AI model from the dropdown (e.g., *Gemini 2.0 Flash*, *Mistral 7B*, *Nvidia Nemotron*, etc.).
   - Click the **Save Configurations** button at the top right.

3. **Generate Summaries**:
   - Go to the **Monitoring** tab.
   - Add your RSS feeds or Telegram channels and make sure they are active.
   - Click the **✨ AI Daily Summary** button located at the top right of the Monitoring view.
   - A global summary card will appear above your feeds, synthesizing the most important events across all your active sources!
</details>

<details>
<summary><b>📱 How to Get Telegram API Credentials</b> (Click to expand)</summary>

To use the Telegram OSINT features, you need a Telegram API ID and Hash. 

1. Go to [https://my.telegram.org/apps](https://my.telegram.org/apps) and log in with your phone number.
2. Click on "API development tools".
3. Create a new application (the name doesn't matter).
4. Copy the **App api_id** and **App api_hash** into your `.env` file (or directly in the application's **Settings** tab).
</details>

---

## 📦 Building for Production

If you want to build the frontend for production (e.g., to serve static files from a production web server):
```bash
cd app
npm run build
```
The compiled assets will be placed in the `app/dist` directory.

---

## 🪟 Windows Installer

You can build a self-contained Windows installer (`.exe`) that bundles Python, all dependencies, ffmpeg, Chromium, and a desktop launcher — no prerequisites needed on the target machine.

**On a Windows machine** (with Node.js and [Inno Setup 6](https://jrsoftware.org/isdl.php) installed):

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1
```

The installer is created at `installer\Output\KNWLDGBox-Setup-<version>.exe`.

Useful options:
- `-Version 1.2.0` — set the installer version
- `-BundleChromium $false` — smaller installer (~170 MB less); the Archives module will then use an installed Chrome or download Chromium on first use
- `-PayloadOnly` — assemble `installer\payload\` without compiling the `.exe`

Notes:
- The app installs to `C:\Program Files\KNWLDGBox` and runs in a native desktop window (PyWebView/Edge WebView2).
- User data (API keys, archives, graphs, downloads) is stored in `%APPDATA%\knwldgbox` and is **not** removed on uninstall.
- Backend logs (useful for troubleshooting) are at `%APPDATA%\knwldgbox\logs\knwldgbox.log`.

---

## 🌟 Key Features

<details>
<summary><b>🔎 Social Forensics</b></summary>

A suite of tools to investigate targets across the internet using just a username or email.
- **Sherlock**: Scan hundreds of social networks and websites to see where a specific username is registered.
- **Maigret**: Build a comprehensive dossier on a target by scraping public information from thousands of sites based on a username.
- **Holehe**: Check if an email address is attached to accounts on platforms like Twitter or Instagram without alerting the target.
- **GHunt**: Extract Google Account data (names, Google Maps reviews, profile IDs) using just a Gmail address.
- **TikTok Scraper**: Download videos, avatars, and metadata associated with specific TikTok usernames or hashtags.
</details>

<details>
<summary><b>🖼️ Image Forensics</b></summary>

A complete, browser-based suite to analyze image manipulation and extract hidden data.
- **Principal Component Analysis (PCA)**: Highlight color and compression inconsistencies to reveal hidden edits or inserted elements.
- **Error Level Analysis (ELA)**: Detect differing JPEG compression levels that indicate a photo has been tampered with.
- **Clone Detection**: Identify regions within an image that have been copy-pasted (cloned).
- **Luminance Gradient & Noise Analysis**: Isolate lighting anomalies, noise patterns, and deformations.
- **EXIF Metadata**: Extract hidden camera data, timestamps, and GPS coordinates from image files.
</details>

<details>
<summary><b>🌐 Target Analysis</b></summary>

Comprehensive domain, IP, and website intelligence gathering.
- **DNS & Ports**: Quickly retrieve DNS records and scan for open ports.
- **SSL & Security**: Analyze SSL Certificate details and Security Headers.
- **Tech Stack**: Detect server technologies and frameworks using Wappalyzer.
- **Wayback Machine**: Check historical snapshots of websites.
- **Geolocation**: Trace IP addresses to physical locations.
</details>

<details>
<summary><b>📥 Media Downloaders</b></summary>

Download high-quality content directly to your server.
- **Universal Downloader**: Uses `yt-dlp` to pull video and audio from YouTube, TikTok, Twitter/X, and Instagram.
- **Cookie Support**: Safely use your own browser's cookies to download age-restricted or private content.
- **Local Media Library**: Browse, preview, and download your scraped media directly from the KNWLDGBox interface.
</details>

<details>
<summary><b>📰 AI-Powered Monitoring & Data Leaks</b></summary>

- **RSS & Telegram Feeds**: Aggregate news and intelligence from active RSS feeds and Telegram channels.
- **OpenRouter AI Summaries**: Use LLMs to generate daily summaries synthesizing the most important events across all your active sources at once.
- **Breach Search**: Search databases of known data leaks to see if specific targets' information has been compromised.
</details>

<details>
<summary><b>🛠️ KNWLDG Tools & Archives</b></summary>

- **Interactive Network Graph**: Create, edit, and explore node-based mind maps to visually trace connections.
- **Local Archives**: An interactive media gallery to explore your saved intelligence screenshots, PDFs, and videos with built-in zooming and panning functionality.
- **Collage Maker**: Generate a composite grid of multiple images with custom watermarks, blurring options, and background colors.
- **Cross Creator**: Visually combine two images with customizable colors and sizes for reports.
</details>

---

## 🔮 Future Work

1. **Expand Tool Ecosystem**: Add more specialized OSINT scraping tools and integrations.
2. **Automated Alerts**: Implement keyword-based desktop or Telegram notifications for active monitoring feeds.

# more to come, you are free to contribute to the project.
