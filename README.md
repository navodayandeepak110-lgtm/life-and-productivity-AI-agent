# 🤖 Deepak AI — Life & Productivity Agent 🚀

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Anthropic-Claude_API-black?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" />
  <img src="https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram" />
  <img src="https://img.shields.io/badge/OmniRoute-Enabled-blueviolet?style=for-the-badge" alt="OmniRoute" />
  <img src="https://img.shields.io/badge/Memory-Multi--Tier_JSON-success?style=for-the-badge" alt="Memory" />
</p>

---

### 🌟 What is this?
An autonomous, long-term memory **AI Life & Productivity Agent** designed to help organize goals, manage deadlines, track daily habits, and execute tasks via **CLI** and **Telegram**! 📱💻

---

### ✨ Key Features 🔥

* 🧠 **Persistent 3-Tier Memory:** Never forgets your goals, projects, notes, and habits across restarts.
* ⚡ **Zero-Token Local Routing:** Instant `0ms` CLI commands (`/today`, `/tasks`, `/radar`, `/habits`) without spending API tokens.
* 🎯 **Dynamic Context Pruning:** Automatically injects only relevant memory for ~60% token savings.
* 📱 **Mobile Telegram Bot:** Manage your life directly from your smartphone with user ID authentication.
* 🌐 **Live Web Search & Scraper:** Real-time web lookups and webpage parsing (DuckDuckGo + BeautifulSoup).
* 📧 **Email Integration:** Read, draft, and send emails safely with IMAP/SMTP.
* 📺 **YouTube Study Tracker:** Track educational video watch time and playlist progress.
* ↩️ **Undo Engine:** Roll back accidental memory changes (up to 5 steps).

---

### 🏗️ Architecture at a Glance 🧩

```text
  User (CLI / Telegram) 📲
          ↓
  Productivity Agent Brain 🧠  ←→  Multi-Tier Memory (agent_data/*.json) 💾
          ↓
  Tool Calling (Web 🌐 | Email 📧 | YouTube 📺 | Tasks 📋)
          ↓
  OmniRoute Proxy (localhost:20128) 🔌
          ↓
  Claude 3.5 / LLM ⚡
```

---

### 🚀 Quickstart 🏁

#### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2️⃣ Setup Environment
```bash
cp .env.example .env
# Fill in ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN & TELEGRAM_BOT_TOKEN
```

#### 3️⃣ Launch 🚀
* **Terminal CLI Mode:**
  ```bash
  python productivity_agent.py
  ```
* **Telegram Bot Mode:**
  ```bash
  python telegram_bot.py
  ```

---

<p align="center">
  <b>Built with ❤️ by Deepak</b> • <i>Supercharging personal productivity with Agentic AI</i> 💡
</p>
