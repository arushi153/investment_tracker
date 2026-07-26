# AI Powered SaT Tool

**Investment Intelligence | Sector Tracking | Location-Based News Discovery**

A Flask-based web application that fetches and analyses global investment news for any Indian state across multiple sectors. It uses Google News RSS feeds and keyword scoring to determine whether news is viable for investment decisions.

---

## Features

- 🔍 **Global News Fetching** — Pulls investment news from Google News (worldwide sources)
- 📍 **All Indian States & UTs** — Select from all 28 states and 8 Union Territories
- 🏭 **Sector Filtering** — Energy, Tourism, Agriculture, Education, Logistics
- ✅ **Viability Badge** — AI keyword scoring marks each article as Viable or Not Viable
- 🖱️ **Clickable Cards** — Click any card to open the full article in a new tab
- 📅 **30-Day Rolling Window** — Always shows the freshest news from the past month

---

## Setup & Run

### Clone & Start (for team members)

```bash
# 1. Clone the repo
git clone https://github.com/arushi153/investment_tracker.git
cd investment_tracker

# 2. Run the one-click setup
bash setup.sh

# 3. Start the app (every time after)
source venv/bin/activate && python app.py
```

Then open **http://127.0.0.1:5000/** in your browser.

> ⚠️ **macOS note:** If you see an SSL error, it is automatically handled by the app. No action needed.

---

## Project Structure

```
ai_powered_sat_tool/
├── app.py               # Flask backend — news fetching & scoring logic
├── keywords.csv         # Investment keywords with weights
├── templates/
│   └── index.html       # Frontend UI
└── requirements.txt     # Python dependencies
```

---

## Keywords

The `keywords.csv` file drives the viability scoring. Add or adjust keywords and weights to tune the AI engine for your investment focus.

| Keyword | Weight |
|---|---|
| mou | 10 |
| investment | 10 |
| expansion | 8 |
| factory | 8 |
| cap-ex | 8 |
| crore | 7 |

---

## Branches

| Branch | Owner |
|---|---|
| `main` | Shared production branch |
| `arushi-dev` | Arushi |
| `aditya-dev` | Aditya |
| `arnav-dev` | Arnav |
