# AI LIFE & PRODUCTIVITY AGENT — COLLEGE PROJECT REPORT

---

## Inventory of All Files and Folders Found in Your Workspace

### Folders:
1. `agent_data/` (Contains subfolders `attachments/`, `exports/`, and JSON databases)
2. `__pycache__/` (Python bytecode cache)

### Source & Core Application Files:
3. `productivity_agent.py` (Main Brain / CLI Agent Engine)
4. `telegram_bot.py` (Telegram Bot Interface & CLI Bridge)
5. `memory_manager.py` (Multi-tiered Memory Subsystem & Storage Engine)
6. `web_tools.py` (DuckDuckGo Web Search & Webpage Scraping Module)
7. `email_tools.py` (IMAP/SMTP Email Reader & Sender Module)
8. `youtube_tools.py` (YouTube Data API & Watch Progress Tracker)

### Configuration, Launchers & Docs:
9. `.env` (Active environment variables & secret keys)
10. `.env.example` (Configuration template for setup)
11. `requirements.txt` (Python dependencies list)
12. `SETUP_INSTRUCTIONS.md` (Complete step-by-step setup documentation)
13. `start-agent.bat` (Windows Command Prompt one-click launcher)
14. `start-agent.cmd` (Windows CMD launcher alias)
15. `start-agent.ps1` (PowerShell one-click launcher)

### Verification & Test Suite Files:
16. `test_omniroute.py` (Tests LLM connectivity through OmniRoute)
17. `test_memory.py` (Tests CRUD memory operations and persistence)
18. `test_temporal.py` (Tests deadline tracking, habit coaching, and timetable)
19. `test_new_features.py` (Unit tests for Web, Email, and YouTube tools)

---

## PROJECT OVERVIEW

**Project Title:** AI Life & Productivity Agent with Persistent Memory & Multi-Channel Interface  
`[IMPLEMENTED NOW]` *(Verified across `productivity_agent.py`, `memory_manager.py`, and `telegram_bot.py`)*

### What it is:
Your project is an autonomous personal productivity and life-management AI agent. Unlike standard chatbots that forget everything when closed, this agent features **persistent multi-tiered memory** (goals, projects, prioritized tasks, habit streaks, daily journals, knowledge notes) and **external tool execution capabilities** (web browsing, live email access, YouTube learning tracker).

It can be accessed simultaneously via:
1. **Interactive Terminal CLI** (with zero-token instant local slash commands + AI chat)
2. **Personal Telegram Bot** (allowing you to control your tasks and schedule from your mobile phone)

It uses **OmniRoute** as a local API gateway to connect with state-of-the-art LLMs (Anthropic Claude / custom models) using Anthropic tool-calling standards.

---

## FILE-BY-FILE EXPLANATION

### 1. `productivity_agent.py`
1. **File Name:** `productivity_agent.py`
2. **Why created:** To serve as the core orchestrator and main execution engine of the AI agent.
3. **What problem it solves:** Standard LLMs cannot manage external state or call local Python tools on their own. This file bridges user queries, memory management, tool definitions, and LLM API calls into an autonomous loop.
4. **What the file does:** Loads configuration, initializes the `Anthropic` client configured to OmniRoute, registers 30+ tools, prunes context dynamically before calling the model, executes tool calls requested by the model, maintains session conversation history, and handles interactive CLI commands (`/today`, `/tasks`, `/briefing`, etc.).
5. **Main classes/functions:**
   - Class: `ProductivityAgent` (Methods: `__init__`, `get_tools()`, `execute_tool()`, `chat()`)
   - Functions: `print_memory_dashboard()`, `print_help_menu()`, `_serialize_content_blocks()`, `main()`
6. **How it connects with other files:**
   - Imports `MemoryManager` from `memory_manager.py`
   - Imports web scrapers from `web_tools.py`
   - Imports email functions from `email_tools.py`
   - Imports YouTube trackers from `youtube_tools.py`
   - Is imported by `telegram_bot.py`
7. **Information stored or processed:** Processes user input prompts, conversation message history arrays, dynamic tool inputs/outputs, and formats memory context into the master system prompt.
8. **Essential or optional:** **Essential** (Core engine of the project).
9. **What happens if removed:** The agent cannot run in CLI, cannot execute LLM tool loops, and the Telegram bot will fail to start.
10. **Simple summary:** The master brain and terminal interface of your AI agent.

---

### 2. `memory_manager.py`
1. **File Name:** `memory_manager.py`
2. **Why created:** To give the AI long-term persistence across restarts so it never forgets your goals, tasks, habits, and notes.
3. **What problem it solves:** Solves the stateless nature and context length limitations of AI models by implementing structured local JSON storage, smart context pruning (reducing token usage by ~60%), and temporal intelligence (deadline alerts).
4. **What the file does:** Manages reading, updating, searching, and saving all data files in `agent_data/`. Provides full CRUD (Create, Read, Update, Delete) methods for tasks, goals, habits, projects, notes, journal entries, and conversations. Implements an Undo stack (up to 5 reversible actions) and keyword search.
5. **Main classes/functions:**
   - Class: `MemoryManager`
   - Key Methods: `load_all()`, `save_all()`, `add_task()`, `update_task()`, `complete_task()`, `add_goal()`, `log_habit()`, `add_journal_entry()`, `save_note()`, `get_pruned_context_summary()`, `get_temporal_briefing()`, `search_all_memory()`, `undo_last_action()`
6. **How it connects with other files:**
   - Used directly by `productivity_agent.py` to supply context to the LLM and execute storage tools.
   - Used directly by `telegram_bot.py` to provide fast local command responses (0ms latency, 0 tokens).
7. **Information stored or processed:** Reads and writes structured dictionaries and lists to JSON files in `agent_data/`.
8. **Essential or optional:** **Essential** (Without this, the agent has zero memory).
9. **What happens if removed:** Every module in the project crashes immediately because memory persistence is required everywhere.
10. **Simple summary:** The storage controller and database manager of the AI system.

---

### 3. `telegram_bot.py`
1. **File Name:** `telegram_bot.py`
2. **Why created:** To allow the user to control the agent and manage daily life remotely from a smartphone via Telegram.
3. **What problem it solves:** Eliminates the need to sit in front of a computer terminal to view tasks, log habits, or talk to the agent.
4. **What the file does:** Uses `python-telegram-bot` to listen for messages. It processes fast local commands (like `/today`, `/tasks`, `/habits`, `/radar`) instantly from `MemoryManager` without consuming API tokens. When a natural language text message is sent, it forwards it to `ProductivityAgent.chat()` and sends the AI's reply back to Telegram. It also contains strict security checks (`is_authorized`) to block unauthorized users.
5. **Main classes/functions:**
   - Functions: `get_agent()`, `is_authorized()`, `start_cmd()`, `today_cmd()`, `tasks_cmd()`, `habits_cmd()`, `add_task_cmd()`, `handle_message()`, `main()`
6. **How it connects with other files:**
   - Imports `ProductivityAgent` from `productivity_agent.py`
   - Imports `MemoryManager` from `memory_manager.py`
   - Imports helpers from `web_tools.py`, `email_tools.py`, `youtube_tools.py`
7. **Information stored or processed:** Handles incoming Telegram `Update` payloads, user IDs, command arguments, and text messages.
8. **Essential or optional:** **Optional for CLI, Essential for Telegram interface.**
9. **What happens if removed:** You can still run the agent via the terminal (`productivity_agent.py`), but you lose mobile/Telegram access.
10. **Simple summary:** The mobile chat and remote control bridge for your AI agent.

---

### 4. `web_tools.py`
1. **File Name:** `web_tools.py`
2. **Why created:** To give the AI agent real-time web access without requiring expensive headless browsers (like Selenium or Puppeteer).
3. **What problem it solves:** LLMs have fixed training cutoffs and cannot browse current articles or websites. This tool gives live internet access.
4. **What the file does:** Performs web queries using DuckDuckGo's Instant Answers / HTML search (no API key required) and fetches webpage HTML using `requests`, stripping out HTML boilerplate and ads using `BeautifulSoup` to return clean text.
5. **Main classes/functions:**
   - Functions: `web_search()`, `read_webpage()`, `format_search_results()`, `format_webpage_result()`, `check_web_tools_available()`, `describe_sensitive_action()`
6. **How it connects with other files:**
   - Called by `productivity_agent.py` when the LLM triggers `web_search` or `read_webpage` tools.
   - Imported into `telegram_bot.py`.
7. **Information stored or processed:** Processes search query strings, HTTP responses, parsed text chunks, and URLs.
8. **Essential or optional:** **Optional (Capability Module)**. The agent runs even without internet scraping.
9. **What happens if removed:** The agent falls back to built-in dummy functions gracefully without crashing, but loses web search capabilities.
10. **Simple summary:** The internet search and webpage reader tool of the agent.

---

### 5. `email_tools.py`
1. **File Name:** `email_tools.py`
2. **Why created:** To integrate standard email functionality (Gmail, Outlook, Yahoo) with the AI assistant.
3. **What problem it solves:** Allows the AI to read your unread inbox emails, summarize messages, draft responses, and send emails securely using standard IMAP/SMTP protocols.
4. **What the file does:** Connects to mail servers over SSL/TLS (ports 993 and 587). Provides safe email listing, searching, draft creation, and sending. Contains safety mechanisms requiring confirmation before sending messages.
5. **Main classes/functions:**
   - Functions: `list_emails()`, `read_email()`, `search_emails()`, `create_draft()`, `send_email()`, `format_email_list()`, `format_email_content()`, `check_email_configured()`
6. **How it connects with other files:**
   - Called by `productivity_agent.py` when the LLM invokes email-related tools.
7. **Information stored or processed:** Processes email headers (Subject, From, Date), email body MIME payloads, and credentials from `.env`.
8. **Essential or optional:** **Optional (Capability Module)**.
9. **What happens if removed:** The agent operates normally for productivity tasks, but email tools will return a missing module message.
10. **Simple summary:** The email assistant module for reading, drafting, and sending emails.

---

### 6. `youtube_tools.py`
1. **File Name:** `youtube_tools.py`
2. **Why created:** To help track educational course progress and YouTube playlist/video study goals.
3. **What problem it solves:** YouTube's API does not expose a user's private watch time history. This tool provides metadata extraction via Google Data API v3 and local JSON watch progress tracking.
4. **What the file does:** Extracts video IDs and playlist IDs from YouTube URLs, parses ISO 8601 video durations (e.g. `PT15M33S` -> `15m 33s`), calculates percentage completed, and persists watch history to `agent_data/youtube_progress.json`.
5. **Main classes/functions:**
   - Functions: `get_video_info()`, `get_playlist_info()`, `track_video_progress()`, `get_video_progress()`, `list_all_tracked_videos()`, `get_playlist_progress()`, `extract_video_id()`, `extract_playlist_id()`, `_iso_duration_to_seconds()`, `_seconds_to_human()`
6. **How it connects with other files:**
   - Invoked by `productivity_agent.py` tool handlers.
   - Saves its data directly inside `agent_data/youtube_progress.json`.
7. **Information stored or processed:** YouTube URLs, video titles, channel names, total duration, seconds watched, completion status, and progress percentages.
8. **Essential or optional:** **Optional (Capability Module)**.
9. **What happens if removed:** Video progress tracking features become unavailable; the rest of the agent continues running.
10. **Simple summary:** The study tracker for YouTube playlists and educational lectures.

---

### 7. Configuration & Launcher Files

#### `.env` & `.env.example`
- **What they do:** `.env` holds the live local environment configurations and secrets (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, `YOUTUBE_API_KEY`, etc.). `.env.example` is the template version.
- **Essential/Optional:** `.env` is **Essential** for credentials; `.env.example` is a documentation template.

#### `requirements.txt`
- **What it does:** Lists the required Python packages (`anthropic`, `python-dotenv`, `python-telegram-bot`, `dateparser`, `requests`, `beautifulsoup4`, `google-api-python-client`).
- **Essential/Optional:** **Essential** for installing project dependencies.

#### `SETUP_INSTRUCTIONS.md`
- **What it does:** Detailed markdown guide explaining how to install packages, configure `.env`, start OmniRoute, run tests, and launch the agent.
- **Essential/Optional:** **Optional** (Documentation).

#### `start-agent.bat`, `start-agent.cmd`, `start-agent.ps1`
- **What they do:** One-click script shortcuts to launch `python productivity_agent.py` on Windows machines.
- **Essential/Optional:** **Optional** convenience launchers.

---

### 8. Test Suite Files

#### `test_omniroute.py`
- **Purpose:** Verifies whether your local OmniRoute proxy server is reachable and responding with LLM completions.
- **Status:** Test utility.

#### `test_memory.py`
- **Purpose:** Verifies that `MemoryManager` can load data, add tasks, record habits, save notes, and perform keyword search on a temporary dataset.
- **Status:** Test utility.

#### `test_temporal.py`
- **Purpose:** Verifies deadline calculations, priority boosts for urgent tasks, habit streak coaching, and timetable formatting.
- **Status:** Test utility.

#### `test_new_features.py`
- **Purpose:** Unit tests for Web search, Email safety rules, and YouTube duration math.
- **Status:** Test utility.

---

## FOLDER STRUCTURE

```
my ai agent/
│
├── agent_data/                      <-- Persistent Storage Database (JSON Files)
│   ├── attachments/                 <-- Stores attached files/documents
│   ├── exports/                     <-- Stores exported summaries/reports
│   ├── context.json                 <-- User profile (name, schedule, college year)
│   ├── goals.json                   <-- Long-term and short-term goals & milestones
│   ├── projects.json                <-- Multi-step project deliverables
│   ├── tasks.json                   <-- Active and completed actionable tasks
│   ├── habits.json                  <-- Daily habits, tracking logs & streaks
│   ├── journal.json                 <-- Daily reflections, wins, study hours
│   ├── notes.json                   <-- Knowledge base notes and custom rules
│   ├── conversations.json           <-- Multi-turn session chat history
│   ├── notifications_state.json     <-- Proactive alert timestamps and state
│   └── youtube_progress.json        <-- Watch positions and playlist progress
│
├── __pycache__/                     <-- Python Compiled Bytecode Cache (.pyc)
│
├── productivity_agent.py            <-- Core Agent Engine & CLI Interface
├── memory_manager.py                <-- Long-Term Memory Controller
├── telegram_bot.py                  <-- Telegram Mobile Interface
├── web_tools.py                     <-- Web Search & Scraper Module
├── email_tools.py                   <-- IMAP/SMTP Email Module
├── youtube_tools.py                 <-- YouTube Metadata & Progress Tracker
├── test_omniroute.py                <-- LLM Connectivity Test Script
├── test_memory.py                   <-- Memory Unit Test Suite
├── test_temporal.py                 <-- Temporal Intelligence Test Suite
├── test_new_features.py             <-- Web/Email/YouTube Test Suite
├── requirements.txt                 <-- Python Dependencies
├── SETUP_INSTRUCTIONS.md            <-- Setup & Run Guide
├── .env                             <-- Private Config & API Keys
├── .env.example                     <-- Sample Configuration Template
├── start-agent.bat                  <-- Windows Batch Launcher
├── start-agent.cmd                  <-- Windows CMD Launcher
└── start-agent.ps1                  <-- Windows PowerShell Launcher
```

---

## COMPLETE SYSTEM ARCHITECTURE

```
                      +------------------------------------------+
                      |                   USER                   |
                      +------------------------------------------+
                                    |              |
                    (Terminal CLI)  |              |  (Mobile Chat)
                                    v              v
                      +--------------------+ +--------------------+
                      | productivity_agent | |    telegram_bot    |
                      |   (Interactive)    | | (Telegram Listener)|
                      +--------------------+ +--------------------+
                                    \              /
                                     \            /
                                      v          v
                      +------------------------------------------+
                      |         ProductivityAgent Brain          |
                      |   - Prunes Context Dynamically           |
                      |   - Assembles System & User Prompts      |
                      +------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
+---------------------------------------+   +---------------------------------------+
|             MEMORY SYSTEM             |   |             TOOL SYSTEM               |
|            (MemoryManager)            |   |                                       |
|                                       |   | • Memory Tools (add/update/delete)   |
| • context.json (User profile)         |   | • Temporal Tools (radar/briefing)    |
| • tasks.json & goals.json             |   | • web_tools (DuckDuckGo + BS4)        |
| • habits.json & journal.json          |   | • email_tools (IMAP + SMTP)           |
| • notes.json & conversations.json     |   | • youtube_tools (YouTube API v3)      |
+---------------------------------------+   +---------------------------------------+
                    \                                             /
                     \                                           /
                      +--------------------+--------------------+
                                           |
                                           v
                      +------------------------------------------+
                      |                OmniRoute                 |
                      |   (Local Gateway Proxy: localhost:20128) |
                      +------------------------------------------+
                                           |
                                           v
                      +------------------------------------------+
                      |                 AI Model                 |
                      |   (Claude 3.5 / Deepak-AI Model)         |
                      +------------------------------------------+
                                           |
                                           v
                      +------------------------------------------+
                      |           Formatted Response             |
                      |    (CLI Display / Telegram Message)      |
                      +------------------------------------------+
```

---

## COMPLETE MESSAGE FLOW

When you send a message (e.g., *"Add a high priority task to finish my DBMS project by Friday"*), here is the exact step-by-step lifecycle:

```
Step 1: Ingestion
  User enters text via CLI (productivity_agent.py) or Telegram (telegram_bot.py).

Step 2: Reception & Interception
  - Fast CLI Check: If the message starts with '/' or matches a command number (e.g. '/today'), 
    it is executed locally by memory_manager.py in 0ms without calling the AI.
  - If it is natural language, it enters ProductivityAgent.chat(user_message).

Step 3: History & Context Pruning
  - The message is appended to self.conversation_history.
  - History is compacted using compact_history().
  - MemoryManager scans the user prompt for keywords (e.g., "task", "DBMS") and extracts 
    only the relevant slice of user data (get_pruned_context_summary), saving ~60% tokens.

Step 4: System Prompt Assembly
  - The master system prompt is formatted with the current Indian Standard Time (IST) 
    and the pruned memory snapshot.

Step 5: AI Model Request via OmniRoute
  - An HTTP request is sent using the Anthropic SDK to http://localhost:20128 (OmniRoute).
  - The request payload contains the System Prompt, Conversation History, and 30+ registered Tool Schemas.

Step 6: Tool Decision & Autonomous Execution Loop
  - The AI model recognizes the intent to create a task.
  - Instead of returning plain text, it returns stop_reason="tool_use" with tool name add_task 
    and parameters: {"title": "Finish DBMS project", "priority": "high", "deadline": "Friday"}.
  - ProductivityAgent.execute_tool() calls MemoryManager.add_task().
  - MemoryManager updates tasks.json and writes changes to disk immediately.
  - The tool execution output (e.g. "Task #12 created") is sent back to the AI model.

Step 7: Final Response Generation
  - The model generates a polite, human-readable confirmation.
  - The complete turn is saved in agent_data/conversations.json.

Step 8: Output Delivery
  - The response is printed to the terminal console or sent to your Telegram chat.
```

---

## MEMORY FLOW

The memory system in `memory_manager.py` operates on **three distinct tiers**:

```
+--------------------------------------------------------------------------------+
| TIER 1: Working / Ephemeral Session Memory                                     |
| • Active multi-turn chat messages within the current running conversation      |
| • Managed in-memory and automatically compacted to avoid token limits          |
+--------------------------------------------------------------------------------+
                                      |
                                      v
+--------------------------------------------------------------------------------+
| TIER 2: Structured Entity Memory (Persistent JSON Databases)                   |
| • Goals (goals.json)         • Tasks (tasks.json)       • Habits (habits.json) |
| • Projects (projects.json)   • Context (context.json)   • Journal (journal.json|
| Updated instantly with disk-sync on every create/update/delete operation.      |
+--------------------------------------------------------------------------------+
                                      |
                                      v
+--------------------------------------------------------------------------------+
| TIER 3: Knowledge Base & Semantic Search                                       |
| • notes.json (Technical concepts, guidelines, study material)                  |
| • Searchable via search_all_memory() and search_notes() with keyword indexing. |
+--------------------------------------------------------------------------------+
```

### Dynamic Pruning (How it saves tokens):
Instead of dumping all your tasks, notes, habits, and journals into every single AI query (which would quickly exceed token limits and cost more), `get_pruned_context_summary()` inspects what you are talking about:
- If you ask about tasks, it injects active tasks and deadlines.
- If you ask about habits, it injects habit streaks.
- If you ask a general question, it provides only high-level summary counts.

---

## TOOL SYSTEM

All tools are implemented in Python and exposed to the AI model via JSON Schema definitions:

| Tool Name | Source Module | Purpose / Action | Status |
|---|---|---|---|
| `add_task`, `update_task`, `complete_task`, `delete_task` | `memory_manager.py` | Full Task Lifecycle Management | `[IMPLEMENTED NOW]` |
| `add_goal`, `update_goal`, `delete_goal` | `memory_manager.py` | Goal & Milestone Tracking | `[IMPLEMENTED NOW]` |
| `log_habit`, `add_habit` | `memory_manager.py` | Habit Logging & Streak Calculation | `[IMPLEMENTED NOW]` |
| `add_journal_entry`, `get_journal_entries` | `memory_manager.py` | Daily Reflections & Study Logs | `[IMPLEMENTED NOW]` |
| `save_note`, `search_notes`, `search_all_memory` | `memory_manager.py` | Knowledge Base CRUD & Search | `[IMPLEMENTED NOW]` |
| `get_temporal_briefing`, `get_deadline_radar` | `memory_manager.py` | Morning Briefing & Deadline Alerts | `[IMPLEMENTED NOW]` |
| `web_search`, `read_webpage` | `web_tools.py` | Live DuckDuckGo search & Web scraping | `[IMPLEMENTED NOW]` |
| `read_emails`, `create_email_draft`, `send_email` | `email_tools.py` | IMAP/SMTP Email Processing | `[IMPLEMENTED NOW]` |
| `get_youtube_video_info`, `track_video_progress` | `youtube_tools.py` | YouTube Info & Study Tracker | `[IMPLEMENTED NOW]` |
| `undo_last_action` | `memory_manager.py` | Reverts last 5 accidental memory changes | `[IMPLEMENTED NOW]` |

---

## IMPORTANT FILES (To Understand First for Your Presentation)

1. **`productivity_agent.py`**: Start here. It shows the main loop, how the AI is prompted, and how tool results are handled.
2. **`memory_manager.py`**: The core data layer. Understand how tasks, goals, and habits are stored as JSON files and loaded dynamically.
3. **`telegram_bot.py`**: Shows how the agent is made accessible remotely via mobile phone.

---

## UNUSED OR TEST FILES

The following files are **verification suites, testing scripts, and launcher shortcuts** (they are not part of the active live runtime loop):
- `test_omniroute.py` — Standalone connection test for OmniRoute.
- `test_memory.py` — Standalone unit test for `memory_manager.py`.
- `test_temporal.py` — Standalone unit test for deadline math and streak coaching.
- `test_new_features.py` — Standalone unit test for web, email, and YouTube utilities.
- `start-agent.bat`, `start-agent.cmd`, `start-agent.ps1` — Convenience shell launchers.

---

## STATUS BREAKDOWN & POTENTIAL IMPROVEMENTS

### Current Feature Status:
- `[IMPLEMENTED NOW]` Persistent multi-tiered JSON memory (Tasks, Goals, Habits, Notes, Journal).
- `[IMPLEMENTED NOW]` OmniRoute API integration with tool-calling loops.
- `[IMPLEMENTED NOW]` Dual Interface: Rich CLI + Telegram Bot with user ID authentication.
- `[IMPLEMENTED NOW]` Zero-token local command routing (0ms latency).
- `[IMPLEMENTED NOW]` Web search (DuckDuckGo) and Webpage reader (BeautifulSoup).
- `[IMPLEMENTED NOW]` IMAP / SMTP email handling with draft creation safety guards.
- `[IMPLEMENTED NOW]` YouTube Data API v3 integration and watch progress tracking.
- `[PARTIALLY IMPLEMENTED]` Google Calendar synchronization (`SETUP_INSTRUCTIONS.md` and dependencies mention Google API client, but primary calendar features currently use local JSON tracking).

### Suggested Future Improvements:
1. `[SUGGESTED FUTURE FEATURE]` **Vector Database Integration (RAG):** Upgrade the keyword search in `memory_manager.py` to ChromaDB / FAISS with sentence embeddings for deeper semantic memory retrieval.
2. `[SUGGESTED FUTURE FEATURE]` **Voice Interaction:** Integrate OpenAI Whisper / Telegram Voice note transcription to speak to the agent directly from WhatsApp or Telegram.
3. `[SUGGESTED FUTURE FEATURE]` **Background Cron Proactive Notifications:** Run an asynchronous background scheduler to send automatic morning alarms and evening review reminders to Telegram without requiring the user to prompt first.

---

## FINAL SUMMARY (College Representation Pitch)

> *"My project is an **Autonomous AI Life & Productivity Agent** built with a modular, multi-tiered architecture. Unlike basic AI chatbots that have no long-term memory, my agent acts as a persistent personal assistant. It is powered by Large Language Models via **OmniRoute** and features an independent **Memory Engine** that permanently stores goals, deadlines, tasks, habits, and notes on disk.*
>
> *The system features **dual interfaces**—an interactive terminal console for developer workflows and a secure **Telegram Bot** for mobile access. To minimize API costs, it implements **Smart Context Pruning** (which saves up to 60% in token consumption) and **Zero-Token Local Command Routing** for instant responses.*
>
> *Finally, the agent is equipped with **Function Calling capabilities**, allowing it to autonomously browse the live web, read and draft emails, and track educational YouTube playlists."*
