# Prysm Product Roadmap & Production Enhancements

This document outlines the recommended next steps to take the Prysm stock research prototype to a production-grade product ("Prysm Pro").

## 1. Production Hardening (Technical Robustness)

_The current app is a solid prototype, but these steps are required for stability at scale._

### 🛡️ Data Integrity & Caching (Critical)

- **Replace `yfinance`**: The generic library is unreliable for production.
  - _Action_: Integrate a professional API like **Polygon.io**, **Alpha Vantage**, or **Kite Connect (Zerodha)** for Indian markets.
- **Redis Caching Layer**: Replace the Python in-memory `DATA_CACHE` with a Redis instance.
  - _Benefit_: Persists cache across server restarts, allows multiple worker processes, and handles expiry automatically.
- **Rate Limiting**: Implement sliding-window rate limiting on the API to prevent abuse (e.g., max 50 queries/hour per free user).

### 🏗️ Infrastructure & DevOps

- **Dockerization**: Create `Dockerfile` and `docker-compose.yml` for the Backend (Node), Agent (Python), and Frontend parts to ensure identical dev/prod environments.
- **Queue System (Celery/BullMQ)**: Move heavy AI tasks (like "Analyze last 5 years of news") to a background queue so the chat doesn't time out.

### 🔐 Security and Auth

- **User Authentication**: Add Supabase or Firebase Auth.
  - _Benefit_: Sync chat history across devices, personalized watchlists.
- **Input Sanitization**: Ensure the prompt injection protection is robust (Guardrails).

---

## 2. New AI Features (The "Wow" Factor)

_Enhancements to make the AI smarter and more helpful._

### 🧠 RAG for Annual Reports ("Research 2.0")

Allow users to upload PDF Annual Reports or Earnings Call Transcripts.

- **Feature**: "Upload Reliance's 2024 Annual Report and summarize the Chairman's message."
- **Tech**: Use `LangChain` document loaders + vector store (ChromaDB/Pinecone) to let the AI "read" specific docs.

### ⚔️ Stock Comparison Engine

- **Feature**: "Compare HDFC Bank vs ICICI Bank"
- **UI**: Render a side-by-side comparison table (Metric vs Metric) and a dual-line chart (identifying relative performance).
- **Tech**: The Agent needs a `compare_stocks` tool that fetches data for 2 tickers and synthesizes a diff.

### 📡 Real-Time News Sentiment Stream

- **Feature**: Instead of pulling news only when asked, run a background job that tracks sentiment for the user's "Watchlist".
- **UI**: A "Live Feed" ticker at the top of the chat showing sentiment alerts (e.g., "⚠️ Breaking: Bearish news for INFY").

---

## 3. UI/UX Polishing

_Visual and functional improvements._

- **TradingView Chart Integration**: Replace `Recharts` with the `TradingView Lightweight Charts` library for a professional "trader" feel (candlesticks, drawing tools).
- **Export Reports**: A button to "Download Analysis as PDF". Converts the chat session + charts into a nicely formatted PDF report for the user to save.
- **Voice Mode**: "Talk to Prysm". Use the Web Speech API to let users ask questions verbally.

## 4. Suggested Immediate Next Step

If you want to tackle one **high-impact** feature next, I recommend **Stock Comparison**. It leverages the existing infrastructure but adds a massive new use case that most simple bots fail at.
