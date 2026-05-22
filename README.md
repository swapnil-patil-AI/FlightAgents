# FlightAgents AI ✈

A multi-agent flight booking system built with **LangGraph** and **Streamlit**, powered by Claude AI. Three specialized AI agents collaborate to search, book, and confirm flights end-to-end.

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────┐
│  Agent 1: Flight Search  │  ← Tavily web search for best flight rates
└────────────┬────────────┘
             │  flight_results
             ▼
┌─────────────────────────┐
│  Agent 2: Booking        │  ← Books selected flight, generates confirmation
└────────────┬────────────┘
             │  booking_confirmation
             ▼
┌─────────────────────────┐
│  Agent 3: Confirmation   │  ← Verifies booking + sends email via Gmail SMTP
└─────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent orchestration | LangGraph |
| LLM | Claude (claude-sonnet-4-6) |
| Flight search | Tavily Search API |
| Email | Gmail SMTP |
| UI | Streamlit |
| Hosting | Streamlit Community Cloud |

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/swapnil-patil-AI/FlightAgents.git
cd FlightAgents
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required keys:
- `ANTHROPIC_API_KEY` — [console.anthropic.com](https://console.anthropic.com/)
- `TAVILY_API_KEY` — [tavily.com](https://tavily.com/)
- `GMAIL_USER` — Your Gmail address
- `GMAIL_APP_PASSWORD` — [Gmail App Password](https://myaccount.google.com/apppasswords) (not your regular password)

### 4. Run locally

```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set main file to `app.py`
4. Add secrets in **Settings → Secrets**:

```toml
ANTHROPIC_API_KEY = "..."
TAVILY_API_KEY    = "..."
GMAIL_USER        = "..."
GMAIL_APP_PASSWORD = "..."
```

## Project Structure

```
FlightAgents/
├── app.py                       # Streamlit UI
├── graph/
│   ├── state.py                 # Shared LangGraph state schema
│   └── workflow.py              # Graph assembly
├── agents/
│   ├── flight_search_agent.py   # Agent 1 — web search
│   ├── booking_agent.py         # Agent 2 — booking
│   └── confirmation_agent.py    # Agent 3 — verify + email
├── tools/
│   ├── search_tools.py          # Tavily search tools
│   ├── booking_tools.py         # Simulated booking tools
│   └── email_tools.py           # Gmail SMTP email tool
├── requirements.txt
├── .env.example
└── .gitignore
```

## Gmail App Password Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create a new App Password for "Mail"
4. Use the 16-character password as `GMAIL_APP_PASSWORD`

## Notes

- Flight booking is **simulated** — no real money is charged
- Flight prices are sourced from public web data via Tavily and may not reflect live GDS prices
- Confirmation emails are sent to the passenger email + `swpnl_ptl2@yahoo.com`
