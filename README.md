# 🤖 Softlight AI Automation Framework

## Why This Fits the Softlight Take-Home

This project was built specifically for the Softlight take-home assignment.

It focuses on:

-  Generalizable browser agent (no hardcoded app workflows)
-  Capturing non-URL UI states (modals, dropdowns, overlays)
-  Session persistence for authenticated apps (Linear, Notion, GitHub)
-  Loop detection & graceful error recovery
-  Dataset of real UI workflows (screenshots + JSON + Markdown)


<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Playwright-1.40+-green.svg" alt="Playwright">
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o-orange.svg" alt="OpenAI">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
  <strong>An AI-powered browser automation framework that captures UI workflows in real-time</strong>
</p>

<p align="center">
  The system navigates web applications autonomously, performs tasks based on natural language commands, and captures screenshots of every UI state — including modals, dropdowns, and forms that don't have unique URLs.
</p>

---

## 🎯 What This Does

Give a natural language command like:

```
"How do I create a project in Linear?"
```

And the AI agent will:
1. **Navigate** to the application
2. **Perform** the required actions (clicks, typing, scrolling)
3. **Capture** screenshots at every step
4. **Save** a complete visual workflow

### The Key Innovation

**Not every UI state has a URL.** Consider creating a project:
- The project list page (has a URL)
- The "Create Project" button state
- The create modal (❌ no URL)
- The form fields (❌ no URL)
- The success state

This framework captures **all** these states by taking screenshots after every action, not just page navigations.

---

## 🏗️ Architecture

```
softlight_automation_framework/
├── softlight_automation_framework/    # Core package
│   ├── agent/                         # AI agent logic
│   │   ├── executor.py               # Main agent execution loop
│   │   ├── prompts.py                # System prompts for LLM
│   │   ├── message_manager.py        # Conversation history
│   │   └── views.py                  # Agent state models
│   │
│   ├── browser/                       # Browser automation
│   │   ├── driver.py                 # Playwright + CDP driver
│   │   ├── session.py                # Session management
│   │   ├── events.py                 # Event system
│   │   └── views.py                  # Browser state models
│   │
│   ├── tutorial/                      # UI capture system
│   │   ├── agent.py                  # Tutorial capture agent
│   │   ├── capture.py                # Screenshot capture logic
│   │   └── views.py                  # Workflow data models
│   │
│   ├── llm/                          # LLM integration
│   │   ├── openai_client.py          # OpenAI GPT client
│   │   ├── messages.py               # Message types
│   │   └── schema.py                 # Output schemas
│   │
│   ├── tools/                        # Action system
│   │   ├── registry.py               # Tool registration
│   │   ├── actions.py                # Built-in actions
│   │   └── views.py                  # Action models
│   │
│   ├── dom/                          # DOM processing
│   │   ├── extractor.py              # DOM extraction
│   │   └── serializer.py             # DOM serialization
│   │
│   └── core/                         # Core utilities
│       ├── config.py                 # Configuration
│       ├── exceptions.py             # Custom exceptions
│       └── logging.py                # Logging setup
│
├── datasets/                          # Captured UI workflows
├── examples/                          # Example scripts
├── run_agent.py                       # Main entry point
├── run.sh                            # Easy runner script
└── requirements.txt                   # Dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/abhiroop-sudansh/softlight-automation-framework.git
   cd softlight-automation-framework
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

5. **Set up environment variables**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   
   Or create a `.env` file:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

### Running the Agent

**Interactive Mode** (recommended for demos):
```bash
./run.sh
```

**Single Command Mode**:
```bash
python run_agent.py -c "Create a new project in Linear"
```

---

## 📖 Usage Examples

### Example 1: Create a Project in Linear
```bash
python run_agent.py -c "How do I Create a new project named 'Softlight AI Automation' with summary 'New Era in AI' in Linear?"
```

### Example 2: Create an Issue in Linear
```bash
python run_agent.py -c "How can I Create a new issue titled 'Fix login bug' with priority High in Linear?"
```

### Example 3: Filter a Database in Notion
```bash
python run_agent.py -c "How do I filter a database in Notion?"
```

### Example 4: Search on GitHub
```bash
python run_agent.py -c "How can I Search for 'tensorflow' repositories on GitHub and sort by stars?"
```

### Example 5: Interactive Session
```bash
./run.sh

# Then type commands:
Agent A: Create a new project in Linear
Agent A: Now filter issues by status
Agent A: quit
```

---

## 📸 Dataset Structure

Each task creates a folder with captured UI states:

```
datasets/
├── how_do_i_create_a_new_project_named_softlight_ai/
│   ├── screenshots/
│   │   ├── step_001.png    # Initial navigation
│   │   ├── step_002.png    # Click Projects
│   │   ├── step_003.png    # Modal opens (no URL change!)
│   │   ├── step_004.png    # Form filled
│   │   └── step_005.png    # Project created
│   ├── workflow.json       # Structured data
│   └── workflow.md         # Human-readable summary
```

### Sample Captured Workflows

| Task | App | Screenshots | Non-URL States Captured |
|------|-----|-------------|------------------------|
| Create Project | Linear | 10 | Modal, form fields |
| Create Issue | Linear | 8 | Priority dropdown, labels |
| Filter Database | Notion | 10 | Filter popover, property selector |
| Search Repos | GitHub | 8 | Search dropdown, sort menu |

---

## 🧠 How It Works

### 1. Natural Language Understanding
The agent uses GPT-4o to understand your intent and plan actions.

### 2. DOM Analysis
Extracts interactive elements from the page with their properties:
- Element type (button, input, link)
- Text content
- ARIA labels
- Position coordinates

### 3. Action Execution
Performs browser actions using Playwright:
- `click` - Click on elements
- `type` - Enter text
- `scroll` - Scroll the page
- `navigate` - Go to URLs
- `press_key` - Keyboard input

### 4. State Capture
After **every action**, the system:
- Takes a screenshot
- Records the action taken
- Saves metadata (URL, title, timestamp)

### 5. Loop Detection
Prevents infinite loops by detecting repeated actions and breaking out gracefully.

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | Model to use | `gpt-4o` |
| `BROWSER_HEADLESS` | Run browser headlessly | `false` |

### Command Line Options

```bash
python run_agent.py --help

Options:
  -c, --command TEXT    Single command to execute
  --headless           Run browser in headless mode
  --keep-open          Keep browser open after task
  --help               Show this message and exit
```

---

## 🔧 Key Features

### ✅ Generalizable
Works on any web application without hardcoded selectors or workflows.

### ✅ Non-URL State Capture
Captures modals, dropdowns, and other ephemeral UI elements.

### ✅ Session Persistence
Save and load login sessions to work with authenticated apps.

### ✅ Loop Detection
Automatically detects and breaks out of repetitive action loops.

### ✅ Error Recovery
Handles navigation errors, loading overlays, and timing issues.

### ✅ Interactive Mode
Chain multiple commands in a persistent browser session.

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `playwright` | ≥1.40.0 | Browser automation |
| `openai` | ≥1.0.0 | GPT API client |
| `pydantic` | ≥2.0.0 | Data validation |
| `python-dotenv` | ≥1.0.0 | Environment variables |
| `rich` | ≥13.0.0 | Terminal formatting |
| `click` | ≥8.0.0 | CLI framework |

Full list in `requirements.txt`.

---

## 🎥 Demo

> 📹 **[Watch the Demo Video on Loom](YOUR_LOOM_LINK_HERE)** ← *Replace with your Loom link*

See the agent navigate Linear, Notion, and GitHub autonomously!

---

## 📁 Project Structure

```
.
├── softlight_automation_framework/   # Main package
├── datasets/                         # Captured workflows
├── examples/                         # Example scripts
├── run_agent.py                      # Entry point
├── run.sh                           # Shell runner
├── requirements.txt                  # Dependencies
├── setup.py                         # Package setup
└── README.md                        # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- Powered by [OpenAI GPT-4o](https://openai.com/) for intelligent decision making
- Inspired by browser automation research and multi-agent systems

---

<p align="center">
  Made with ❤️ for the future of AI automation
</p>
