# 📸 UI State Capture Dataset

This dataset contains captured UI workflows from real web applications. Each workflow demonstrates the system's ability to capture states that **don't have unique URLs** — modals, dropdowns, form fields, and other ephemeral UI elements.

---

## 📊 Dataset Summary

| # | Task | Application | Screenshots | Key States Captured |
|---|------|-------------|-------------|---------------------|
| 1 | Create Project | Linear | 10 | Modal popup, form fields, submit |
| 2 | Create Issue | Linear | 8 | Issue modal, priority dropdown, labels |
| 3 | Filter Database | Notion | 10 | Filter popover, property selector, value picker |
| 4 | Search & Sort Repos | GitHub | 8 | Search dropdown, results, sort menu |

**Total: 36+ screenshots across 4 workflows**

---

## 📁 Folder Structure

```
datasets/
├── README.md
├── 01_create_project_in_linear/
│   ├── screenshots/
│   │   ├── step_001.png
│   │   ├── step_002.png
│   │   └── ...
│   ├── workflow.json
│   └── workflow.md
├── 02_create_issue_in_linear/
│   └── ...
├── 03_filter_database_in_notion/
│   └── ...
└── 04_search_repos_on_github/
    └── ...
```

---

## 🔍 Detailed Task Descriptions

### Task 1: Create a Project in Linear

**Command:** `"How do I Create a new project named 'Softlight AI Automation' with summary 'New Era in AI' in Linear?"`

**What this demonstrates:**
- Navigation to project section
- Opening "Add Project" modal (no URL change!)
- Typing in form fields
- Submitting the form

**Non-URL states captured:**
- ✅ Create project modal overlay
- ✅ Form input states during typing
- ✅ Success confirmation

---

### Task 2: Create an Issue in Linear

**Command:** `"How can I Create a new issue titled 'Fix login bug' with priority High in Linear?"`

**What this demonstrates:**
- Opening issue creation modal
- Setting issue title
- Selecting priority from dropdown
- Applying labels

**Non-URL states captured:**
- ✅ Issue creation modal
- ✅ Priority dropdown menu
- ✅ Label selector popover

---

### Task 3: Filter a Database in Notion

**Command:** `"How do I filter a database in Notion?"`

**What this demonstrates:**
- Navigating to a database view
- Opening filter interface
- Selecting filter properties
- Applying filter values

**Non-URL states captured:**
- ✅ Filter button popover
- ✅ Property selector dropdown
- ✅ Value picker dropdown
- ✅ Applied filter state

---

### Task 4: Search Repositories on GitHub

**Command:** `"How can I Search for 'tensorflow' repositories on GitHub and sort by stars?"`

**What this demonstrates:**
- Using GitHub search
- Viewing search results
- Opening sort dropdown
- Selecting sort option

**Non-URL states captured:**
- ✅ Search suggestions dropdown
- ✅ Sort menu dropdown
- ✅ Filtered results state

---

## 🎯 Key Insight: Capturing Non-URL States

Traditional web scraping and automation tools rely on URLs to identify pages. But modern web applications use:

- **Modals** - Overlay dialogs that don't change the URL
- **Dropdowns** - Temporary menus that disappear after selection
- **Popovers** - Contextual panels attached to elements
- **Form states** - Input values that exist only in memory

This system captures **all** of these by taking screenshots after **every action**, not just after page navigations.

---

## 🔄 How States Are Captured

```
User Command
     ↓
AI Plans Actions → Execute Action 1 → 📸 Screenshot
                 → Execute Action 2 → 📸 Screenshot
                 → Execute Action 3 → 📸 Screenshot
                 → ...
                 → Task Complete
     ↓
Workflow Saved (screenshots + metadata)
```

Each screenshot includes:
- Timestamp
- Current URL
- Page title
- Action that triggered it
- Agent's reasoning

---

## 🚀 Generalizability

This system is **not hardcoded** for any specific application. The same approach works for:

- ✅ Any SaaS application (Asana, Trello, Jira, etc.)
- ✅ Any e-commerce site (Amazon, Shopify stores)
- ✅ Any content platform (YouTube, Reddit, etc.)
- ✅ Any custom web application

To capture a new workflow, simply provide a natural language command describing the task.

