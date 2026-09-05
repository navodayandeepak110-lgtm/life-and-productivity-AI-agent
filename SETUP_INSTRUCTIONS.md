# AI Life & Productivity Agent - Setup Instructions

## Complete Setup Guide for OmniRoute Integration

---

## STEP 1: Install Python Dependencies

Open PowerShell in this directory and run:

```powershell
pip install -r requirements.txt
```

This installs:
- `anthropic` - Anthropic SDK for Claude API
- `python-dotenv` - Environment variable management

---

## STEP 2: Create Your .env File

Copy the example file and configure it:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` with your actual values:

```
ANTHROPIC_BASE_URL=http://localhost:20128
ANTHROPIC_AUTH_TOKEN=your-actual-token-here
ANTHROPIC_MODEL=deepak-ai
```

**Important:** 
- Replace `your-actual-token-here` with your real OmniRoute auth token
- Adjust the port if your OmniRoute uses a different one
- The model name should match what's configured in OmniRoute

---

## STEP 3: Test OmniRoute Connection

Verify everything is working:

```powershell
python test_omniroute.py
```

**Expected output:**
```
============================================================
OMNIROUTE CONNECTION TEST
============================================================

✓ Base URL: http://localhost:20128
✓ Model: deepak-ai
✓ Auth token: ********************

🔄 Testing connection to OmniRoute...

✅ SUCCESS!
Response from deepak-ai:
  OmniRoute connection successful!

✓ OmniRoute is working correctly!
✓ Using local endpoint: http://localhost:20128
✓ Model: deepak-ai
```

If you see this, you're ready to go! If not, check the troubleshooting section below.

---

## STEP 4: Run the Productivity Agent

```powershell
python productivity_agent.py
```

You should see:

```
============================================================
AI LIFE & PRODUCTIVITY AGENT
Powered by OmniRoute
============================================================

Initializing agent...
✓ Connected to OmniRoute at http://localhost:20128
✓ Using model: deepak-ai
✓ Agent ready!

Type 'quit' or 'exit' to end the conversation.

You: 
```

---

## STEP 5: Start Using Your Agent

Try these commands:

**Set a goal:**
```
I want to learn machine learning in 6 months
```

**Get today's plan:**
```
What should I focus on today?
```

**Add a task:**
```
Add task: Read Python ML tutorial
```

**Track progress:**
```
I completed task 1
```

**Weekly review:**
```
Give me a weekly review
```

---

## Troubleshooting

### Error: "ANTHROPIC_BASE_URL not found"
- Make sure you created the `.env` file
- Check that `.env` is in the same directory as `productivity_agent.py`

### Error: "Connection failed"
- Verify OmniRoute is running: check if `http://localhost:20128` is accessible
- Try accessing the URL in your browser
- Check the port number matches your OmniRoute configuration

### Error: "Authentication failed"
- Verify your `ANTHROPIC_AUTH_TOKEN` is correct
- Check for extra spaces or quotes in the `.env` file

### Error: "Model not found"
- Verify the model name matches your OmniRoute configuration
- Check OmniRoute logs for available models

---

## Quick Command Reference

### Install dependencies:
```powershell
pip install -r requirements.txt
```

### Test connection:
```powershell
python test_omniroute.py
```

### Run agent:
```powershell
python productivity_agent.py
```

### View your data:
Check the `agent_data/` folder for:
- `goals.json` - Your goals
- `tasks.json` - Your tasks
- `projects.json` - Your projects
- `habits.json` - Your habits
- `context.json` - Personal context

---

## Security Notes

✅ **Good practices:**
- `.env` file is gitignored (never commit secrets)
- Authentication token loaded from environment
- No credentials hardcoded in the code

⚠️ **Keep your .env file secure:**
- Never share it
- Never commit it to version control
- Never upload it anywhere

---

## What Makes This Different from Standard Claude?

🔒 **Privacy:** All requests go to YOUR local OmniRoute server
🎯 **Custom Model:** Uses your configured `deepak-ai` model
⚡ **Local Control:** No data leaves your machine
🔧 **Customizable:** Full control over routing and model behavior

Your agent connects to OmniRoute at `http://localhost:20128` instead of Anthropic's cloud API.

---

## Need Help?

1. Check that OmniRoute is running
2. Run the test script: `python test_omniroute.py`
3. Check the `.env` file configuration
4. Review the error messages carefully

The agent will tell you exactly what's wrong!
