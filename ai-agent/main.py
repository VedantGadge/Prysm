import os
import json
import uuid
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator, Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# LangGraph & LangChain Imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from graph import graph

# Tool Imports for Auto-Inject
from tools import generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis, compare_stocks, consult_knowledge_base
from stock_data import get_stock_data, generate_price_history
from rag_service import process_pdf, clear_db as clear_rag_db

# MONGODB Imports
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env from backend directory (Robust)
from pathlib import Path
possible_paths = [
    Path(__file__).resolve().parent.parent / "backend" / ".env",
    Path.cwd() / "backend" / ".env",
    Path.cwd() / "../backend" / ".env",
]
env_path = None
for p in possible_paths:
    if p.exists():
        env_path = p
        break
if env_path: load_dotenv(dotenv_path=env_path, override=True)

app = FastAPI(title="Prysm AI Agent (LangGraph + Mongo)", version="2.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MONGO_URI = os.getenv("MONGO_URI")

# --- MONGODB CONNECTION ---
client_mongo = None
db = None

@app.on_event("startup")
async def startup_db_client():
    global client_mongo, db
    if MONGO_URI:
        try:
            client_mongo = AsyncIOMotorClient(MONGO_URI)
            # Use explicit database name
            db = client_mongo["prysm"]  # Explicit database name
            print(f"Connected to MongoDB: prysm")
        except Exception as e:
            print(f"MongoDB Connection Failed: {e}")
    else:
        print("WARNING: MONGO_URI not found.")

@app.on_event("shutdown")
async def shutdown_db_client():
    if client_mongo:
        client_mongo.close()

# --- HELPER: Intent Extraction ---
from google import genai
from google.genai import types
import re

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_gemini = None
if GEMINI_API_KEY:
    try:
        client_gemini = genai.Client(api_key=GEMINI_API_KEY)
    except:
        pass

async def extract_intent(message: str, history: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    # Build history context and find last mentioned stock
    history_summary = ""
    last_stock = None
    
    print(f"[INTENT] History length: {len(history)}")
    
    for turn in history[-10:]: # Look deeper: last 10 turns
        role = turn.get('role', 'user')
        text = turn.get('parts', [{}])[0].get('text', '')
        history_summary += f"{role}: {text[:150]}...\n"
        
        # Look for stock mentions in both user and model text
        # Scan for common ticker patterns
        tickers = re.findall(r'\b[A-Z]{2,6}\b', text.upper())
        # Filter out common words like "THE", "AND", "FOR", "STOCK", "PRICE", "CHART"
        COMMON_WORDS = {"THE", "AND", "FOR", "STOCK", "PRICE", "CHART", "RISK", "WHAT", "SHOW", "GIVE", "TELL", "HAVE", "COPY", "WITH", "FROM", "THAT", "THIS", "YOUR", "DEEP", "DIVE", "INTO", "ASSESSMENT", "ANALYSIS", "BULLISH", "BEARISH", "SENTIMENT", "TIMELINE", "FUTURE", "OUTLOOK"}
        candidates = [t for t in tickers if t not in COMMON_WORDS]
        if candidates:
            last_stock = candidates[-1] # Take the most recent one
            
    print(f"[INTENT] Last stock found in context: {last_stock}")
    
    intent_prompt = f"""You are parsing a user query about stocks. Extract the ACTUAL stock ticker symbol and intent.

User message: "{message}"
Previous context stock: {last_stock if last_stock else "None"}
Recent conversation: {history_summary[:300] if history_summary else "None"}

Rules:
- Extract the REAL NSE/BSE stock ticker (e.g., "RELIANCE", "TCS", "INFY", "HDFC")
- If user says "it", "its", "this stock" and there's a previous stock in context, use that stock symbol
- Return the ACTUAL symbol, NOT the word "TICKER"
- If no stock is mentioned or implied, return null

Return ONLY valid JSON:
{{"stock_symbol": "MAIN_TICKER" or null, "second_symbol": "SECOND_TICKER" or null, "intent": "risk/chart/future/sentiment/analysis/comparison/general"}}"""
    
    try:
        if not client_gemini: return {"stock_symbol": None, "intent": "general"}
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client_gemini.models.generate_content(
                model="gemini-2.5-flash", contents=intent_prompt, config=types.GenerateContentConfig(temperature=0.1)
            )
        )
        text = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(text)
        
        print(f"[INTENT] LLM Raw Result: {result}")
        
        # Validate extracted stock symbol - filter out obviously wrong ones
        extracted_symbol = result.get("stock_symbol")
        if extracted_symbol:
            # Filter out common words that are not stocks
            INVALID_SYMBOLS = {"ALSO", "STOCK", "TICKER", "NONE", "NULL", "IT", "ITS", "THIS", "THAT", "DEEP", "DIVE", "INTO", "THE", "ACTUAL"}
            if extracted_symbol.upper() in INVALID_SYMBOLS:
                print(f"[INTENT] Filtered out invalid symbol: {extracted_symbol}")
                result["stock_symbol"] = None

        # STICKY CONTEXT LOGIC - More aggressive
        # If we have a last_stock from context, use it for ANY analysis-type query
        if not result.get("stock_symbol") and last_stock:
            # For ANY intent that's not "general", assume they're continuing the conversation
            if result.get("intent") in ["risk", "chart", "future", "sentiment", "analysis"]:
                print(f"[INTENT] Applying sticky context (intent-based): {last_stock}")
                result["stock_symbol"] = last_stock
            
            # Also apply if the message looks like a follow-up
            elif any(w in message.lower() for w in ["it", "its", "this", "that", "the stock", "details", "more", "deep", "dive", "show", "give", "tell"]):
                print(f"[INTENT] Applying sticky context (pronoun-based): {last_stock}")
                result["stock_symbol"] = last_stock
            
            # Last resort: if message is short (< 50 chars) and we have context, use it
            elif len(message) < 50 and last_stock:
                print(f"[INTENT] Applying sticky context (short query): {last_stock}")
                result["stock_symbol"] = last_stock

        return result
    except Exception as e:
        print(f"[INTENT] Error: {e}")
        # Emergency fallback - if we have context, use it
        if last_stock:
            return {"stock_symbol": last_stock, "intent": "analysis"}
        return {"stock_symbol": None, "intent": "general"}



def create_stock_context(stock_data: dict) -> str:
    if not stock_data: return "No data."
    quote = stock_data.get('quote', {})
    fin = stock_data.get('financials', {}).get('detailed', {})
    ratios = stock_data.get('financials', {}).get('ratios', {})
    shareholding = stock_data.get('shareholding', {})
    company = stock_data.get('companyInfo', {})
    
    # Helper for safe formatting
    def safe_pct(val):
        if val is None: return "N/A"
        try: return f"{float(val):.2f}"
        except: return "N/A"
    
    desc = company.get('description') or "No description available."
    desc = desc[:500] if len(desc) > 500 else desc
    
    context = (
        f"Stock: {quote.get('symbol', 'N/A')} ({company.get('sector', 'N/A')})\n"
        f"Price: {quote.get('price', 'N/A')} (Change: {quote.get('changePercent', 'N/A')}%)\n"
        f"Market Cap: {fin.get('marketCap', 'N/A')}\n"
        f"P/E: {fin.get('trailingPE', 'N/A')} | PEG: {fin.get('pegRatio', 'N/A')} | P/B: {fin.get('priceToBook', 'N/A')}\n"
        f"Margins: Gross {safe_pct(fin.get('grossMargin'))}%, Net {safe_pct(fin.get('netMargin'))}%, Operating {safe_pct(fin.get('operatingMargin'))}%\n"
        f"Returns: ROE {safe_pct(fin.get('returnOnEquity'))}%, ROA {safe_pct(fin.get('returnOnAssets'))}%\n"
        f"Growth: Rev Growth {safe_pct(fin.get('revenueGrowth'))}%, Earnings Growth {safe_pct(fin.get('earningsGrowth'))}%\n"
        f"Balance Sheet: Debt/Eq {fin.get('debtToEquity', 'N/A')}, Current Ratio {fin.get('currentRatio', 'N/A')}\n"
        f"Cash Flow: Operating {fin.get('operatingCashflow', 'N/A')}, Free {fin.get('freeCashflow', 'N/A')}\n"
        f"Shareholding: Promoters {shareholding.get('promoters', 'N/A')}%, FII {shareholding.get('fii', 'N/A')}%, DII {shareholding.get('dii', 'N/A')}%, Public {shareholding.get('public', 'N/A')}%\n"
        f"Description: {desc}..."
    )
    return context


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _compact_title(text: str, max_len: int = 44) -> str:
    t = (text or "").strip()
    if not t:
        return "New Chat"
    t = " ".join(t.split())
    return (t[: max_len - 1] + "…") if len(t) > max_len else t


def _derive_session_title(
    first_user_message: str,
    target_symbol: Optional[str],
    normalized_mode: Optional[str],
    intent: Optional[str],
) -> str:
    msg = (first_user_message or "").strip()
    msg_upper = msg.upper()

    if normalized_mode == "overall":
        if "COMPARE" in msg_upper or " VS " in msg_upper or " V/S " in msg_upper:
            if target_symbol:
                return f"{target_symbol} Comparison".strip()
            return "Comparison"

        # If a stock is selected in UI (passed as target_symbol), reflect it for stock-specific intents.
        if target_symbol and intent in {"risk", "sentiment", "future", "chart", "analysis", "comparison"}:
            suffix = {
                "risk": "Risk",
                "sentiment": "Sentiment",
                "future": "Outlook",
                "chart": "Chart",
                "comparison": "Comparison",
            }.get(intent or "", "Analysis")
            return f"{target_symbol} {suffix}".strip()

        if intent in {"risk", "sentiment", "future", "chart"}:
            return _compact_title(intent.title())
        return "Portfolio / Market" if msg else "New Chat"

    if target_symbol:
        suffix = {
            "risk": "Risk",
            "sentiment": "Sentiment",
            "future": "Outlook",
            "chart": "Chart",
            "comparison": "Comparison",
        }.get(intent or "", "Analysis")
        return f"{target_symbol} {suffix}".strip()

    return _compact_title(msg)


def _derive_preview(user_message: str) -> str:
    return _compact_title(user_message, max_len=70)


def _utc_date_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).date().isoformat()


def _message_ts_to_date_str(msg: Dict[str, Any]) -> Optional[str]:
    ts = msg.get("ts")
    if not ts:
        return None
    try:
        if isinstance(ts, datetime):
            return _utc_date_str(ts)
        # Accept ISO strings
        return _utc_date_str(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
    except Exception:
        return None


async def _summarize_text_with_gemini(text: str) -> Optional[str]:
    if not text or not client_gemini:
        return None
    prompt = (
        "Summarize the following chat for durable storage. "
        "Return a concise snapshot with: bullets for key questions, key answers, tickers discussed, and action items. "
        "Keep it under 1200 characters.\n\n"
        f"CHAT:\n{text}"
    )
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            ),
        )
        out = (response.text or "").strip()
        return out[:1200]
    except Exception as e:
        print(f"[SNAPSHOT] Gemini summarize failed: {e}")
        return None


def _fallback_snapshot(messages: List[Dict[str, Any]]) -> str:
    # Simple deterministic fallback: keep the first/last user prompts and tickers.
    users = [m for m in messages if m.get("role") == "user"]
    models = [m for m in messages if m.get("role") == "model"]
    first_user = (users[0].get("parts", [{}])[0].get("text", "") if users else "").strip()
    last_user = (users[-1].get("parts", [{}])[0].get("text", "") if users else "").strip()
    last_model = (models[-1].get("parts", [{}])[0].get("text", "") if models else "").strip()
    last_model = _compact_title(last_model, max_len=220)

    lines = []
    if first_user:
        lines.append(f"- Started with: {_compact_title(first_user, max_len=140)}")
    if last_user and last_user != first_user:
        lines.append(f"- Ended with: {_compact_title(last_user, max_len=140)}")
    if last_model:
        lines.append(f"- Latest answer snippet: {last_model}")
    if not lines:
        lines.append("- Summary unavailable")
    return "\n".join(lines)


async def _archive_previous_days(session_id: str) -> None:
    """Summarize and prune messages from previous UTC days into snapshots."""
    if db is None:
        return

    session = await db.agent_sessions.find_one({"_id": session_id})
    if not session:
        return

    messages = session.get("messages", []) or []
    if not messages:
        return

    today = _utc_date_str(_now_utc())

    # Group messages by UTC day (only those with timestamps).
    by_day: Dict[str, List[Dict[str, Any]]] = {}
    kept: List[Dict[str, Any]] = []

    for m in messages:
        day = _message_ts_to_date_str(m)
        # If no timestamp, keep it to avoid accidental data loss.
        if not day:
            kept.append(m)
            continue
        if day == today:
            kept.append(m)
            continue
        by_day.setdefault(day, []).append(m)

    if not by_day:
        return

    existing = session.get("snapshots", []) or []
    existing_days = {s.get("date") for s in existing if isinstance(s, dict)}
    new_snapshots = []

    # Summarize each day not yet snapshotted.
    for day in sorted(by_day.keys()):
        if day in existing_days:
            # Already snapshotted; just drop the old messages.
            continue

        day_msgs = by_day[day]
        # Build compact transcript
        transcript_lines = []
        for msg in day_msgs:
            role = msg.get("role", "")
            text = msg.get("parts", [{}])[0].get("text", "")
            if not text:
                continue
            text = " ".join(str(text).split())
            transcript_lines.append(f"{role}: {text}")
        transcript = "\n".join(transcript_lines)
        transcript = transcript[:12000]

        summary = await _summarize_text_with_gemini(transcript)
        if not summary:
            summary = _fallback_snapshot(day_msgs)

        new_snapshots.append({
            "date": day,
            "summary": summary,
            "message_count": len(day_msgs),
            "created_at": _now_utc(),
        })

    # Remove all previous-day timestamped messages regardless (we keep only today's + untimestamped)
    await db.agent_sessions.update_one(
        {"_id": session_id},
        {
            "$set": {"messages": kept, "updated_at": _now_utc()},
            "$push": {"snapshots": {"$each": new_snapshots}} if new_snapshots else {},
        },
        upsert=True,
    )


class ChatRequest(BaseModel):
    message: str
    stock_symbol: Optional[str] = None
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = []
    mode: Optional[str] = None  # 'overall' | 'stock'
    profile: Optional[str] = None  # 'strategic' | 'balanced'


# --- MAIN RESPONSE STREAM ---
async def generate_response_stream(
    message: str,
    session_id: str = None,
    stock_symbol: Optional[str] = None,
    mode: Optional[str] = None,
    profile: Optional[str] = None,
):
    
    # 1. Fetch Session from DB (null-safe)
    session_data = None
    if session_id and db is not None:
        session_data = await db.agent_sessions.find_one({"_id": session_id})
    
    if not session_data:
        # If caller provided a session_id, keep it; otherwise create one.
        session_id = session_id or str(uuid.uuid4())
        session_data = {
            "_id": session_id,
            "title": "New Chat",
            "preview": "",
            "messages": [],
            "created_at": _now_utc(),
            "updated_at": _now_utc(),
        }
        if db is not None:
            await db.agent_sessions.replace_one({"_id": session_id}, session_data, upsert=True)

    # Archive older days into snapshots before adding more turns
    if db is not None:
        try:
            await _archive_previous_days(session_id)
        except Exception as e:
            print(f"[SNAPSHOT] Archive failed: {e}")
    
    # Re-fetch after potential archival
    if db is not None:
        session_data = await db.agent_sessions.find_one({"_id": session_id}) or session_data
    history = session_data.get("messages", [])

    # 2. Intent & Context
    normalized_mode = (mode or "").strip().lower() or None
    normalized_profile = (profile or "").strip().lower() or None

    # If user explicitly chose Overall, reduce sticky-stock behavior by not feeding prior stock context
    intent_history = [] if normalized_mode == "overall" else history
    intent_data = await extract_intent(message, intent_history)

    selected_symbol = (stock_symbol or "").strip() or None
    requested_symbol = intent_data.get("stock_symbol")
    user_intent = intent_data.get("intent", "analysis")

    # Decide whether a ticker is explicitly requested vs merely selected in UI
    enforce_symbol = False
    active_symbol = requested_symbol
    if normalized_mode == "stock" and selected_symbol:
        active_symbol = selected_symbol
        enforce_symbol = True
        user_intent = user_intent or "analysis"
    elif requested_symbol:
        enforce_symbol = True

    contextual_symbol = None
    if not active_symbol and selected_symbol:
        contextual_symbol = selected_symbol

    print(f"[MAIN] Extracted target_symbol: {active_symbol}, intent: {user_intent} (selected={selected_symbol}, enforce={enforce_symbol})")
    
    # Improve session summary on first user message
    if len(history) == 0:
        session_data["title"] = _derive_session_title(message, active_symbol or contextual_symbol, normalized_mode, user_intent)
        session_data["preview"] = _derive_preview(message)
        session_data["updated_at"] = _now_utc()
        if db is not None:
            await db.agent_sessions.update_one(
                {"_id": session_id},
                {"$set": {"title": session_data["title"], "preview": session_data["preview"], "updated_at": session_data["updated_at"]}},
                upsert=True,
            )

    profile_hint = ""
    if normalized_profile == "strategic":
        profile_hint = "\nUser preference: Strategic (long-term, fundamentals, risk-aware)."
    elif normalized_profile == "balanced":
        profile_hint = "\nUser preference: Balanced (moderate risk, avoid extremes, practical tradeoffs)."

    mode_hint = ""
    if normalized_mode == "overall":
        mode_hint = "\nMode: Overall. Provide portfolio-level / general guidance unless the user asks about a specific ticker."
    elif normalized_mode == "stock":
        mode_hint = "\nMode: Stock. Focus on the selected ticker when applicable."

    # Build system prompt.
    # - If a ticker is explicitly requested (or Stock mode is selected), enforce it.
    # - If a ticker is only selected in UI, include it as context without forcing it.
    if active_symbol and enforce_symbol:
        data = get_stock_data(active_symbol)
        context = create_stock_context(data)
        system_prompt_text = f"""You are Prysm, an expert financial analyst.

IMPORTANT: The user is asking about {active_symbol}. You MUST analyze {active_symbol}.
Do NOT ask the user for the ticker - it is {active_symbol}.

Stock Data for {active_symbol}:
{context}

RULES:
1. Use your tools (generate_chart, generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis) to provide visual insights.
2. If the user asks to COMPARE {active_symbol} with another stock (e.g. INFY), **IMMEDIATELY call the `compare_stocks` tool**. Do not say "I don't have data for INFY". The tool will fetch it.
3. If the user attaches a document or asks about a file, use `consult_knowledge_base`.
4. Always provide detailed analysis based on real data.
{mode_hint}{profile_hint}
"""
    elif contextual_symbol:
        data = get_stock_data(contextual_symbol)
        context = create_stock_context(data)
        system_prompt_text = f"""You are Prysm, an expert financial analyst.

Selected stock context: {contextual_symbol}.
The user has selected {contextual_symbol} in the UI. If the user's question is stock-specific but doesn't name a ticker, you may use {contextual_symbol} as the default.
If the user's question is clearly portfolio-level / general, answer generally and do not force everything to be about {contextual_symbol}.

Stock Data for {contextual_symbol} (context only):
{context}

RULES:
1. Use your tools (generate_chart, generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis) to provide visual insights when useful.
2. If the user asks to COMPARE {contextual_symbol} with another stock (e.g. INFY), **IMMEDIATELY call the `compare_stocks` tool**.
3. If the user asks about an uploaded document (PDF, report, annual report), ALWAYS use the `consult_knowledge_base` tool.
{mode_hint}{profile_hint}
"""
    else:
        system_prompt_text = """You are Prysm, an expert financial analyst.
If the user asks about a stock without specifying a ticker, ask them which stock they want to analyze.
If they ask to COMPARE two stocks, immediately use the `compare_stocks` tool (e.g. compare_stocks('TCS', 'INFY')).
If the user asks about an uploaded document (PDF, report, annual report), ALWAYS use the `consult_knowledge_base` tool to search for relevant information before answering.""" + f"{mode_hint}{profile_hint}"

    # 3. Message Construction (LangChain format)
    lc_messages = [SystemMessage(content=system_prompt_text)]
    for turn in history[-5:]: 
        if turn['role'] == 'user': lc_messages.append(HumanMessage(content=turn['parts'][0]['text']))
        else: lc_messages.append(AIMessage(content=turn['parts'][0]['text']))
    
    # 4. AUTO-INJECT (DISABLED to prevent double-tool repetition)
    # The LangGraph agent is smart enough to call these tools itself.
    auto_tools = []
    # if target_symbol:
    #     if user_intent == "risk": auto_tools.append(("risk", generate_risk_gauge))
    #     elif user_intent == "future": auto_tools.append(("future", generate_future_timeline))
    #     elif user_intent == "sentiment": auto_tools.append(("sentiment", generate_sentiment_analysis))
    
    # for _, tool_func in auto_tools:
    #     res = tool_func.invoke({"ticker": target_symbol})
    #     if isinstance(res, dict):
    #         ui = res.get("ui_content", "")
    #         if ui: yield f"data: {json.dumps({'content': ui})}\n\n"
    #         summary = res.get("llm_data", {})
    #         lc_messages.append(SystemMessage(content=f"AUTO-ANALYSIS DATA for {target_symbol}: {json.dumps(summary)}"))

    lc_messages.append(HumanMessage(content=message))

    # 5. EXECUTE GRAPH
    accumulated_text = ""
    inputs = {"messages": lc_messages}
    
    async for event in graph.astream_events(inputs, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            
            # Handle both string and list content
            text_content = ""
            if isinstance(content, str):
                text_content = content
            elif isinstance(content, list):
                text_content = "".join(str(item) if isinstance(item, str) else str(item.get("text", "")) for item in content)
            
            if text_content:
                yield f"data: {json.dumps({'content': text_content})}\n\n"
                accumulated_text += text_content
        elif kind == "on_tool_end":
            output = event["data"].get("output")
            
            # LangGraph's ToolNode wraps output in ToolMessage
            if hasattr(output, 'content'):
                output = output.content
                if isinstance(output, str) and output.startswith("{"):
                    try:
                        output = json.loads(output)
                    except:
                        pass
            
            # Handle both dict and string outputs
            ui = None
            if isinstance(output, dict):
                ui = output.get("ui_content")
            elif isinstance(output, str) and output.startswith("["):
                ui = output
            
            if ui:
                yield f"data: {json.dumps({'content': ui})}\n\n"
                accumulated_text += ui

    # 6. Save to DB (if available)
    now_ts = _now_utc()
    new_messages = [
        {"role": "user", "parts": [{"text": message}], "ts": now_ts},
        {"role": "model", "parts": [{"text": accumulated_text}], "ts": now_ts}
    ]
    if db is not None:
        await db.agent_sessions.update_one(
            {"_id": session_id},
            {
                "$push": {"messages": {"$each": new_messages}},
                "$set": {"preview": _derive_preview(message), "updated_at": now_ts},
                "$setOnInsert": {"title": "New Chat", "created_at": now_ts},
            },
            upsert=True
        )


# --- API ENDPOINTS ---

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        generate_response_stream(
            request.message,
            request.session_id,
            request.stock_symbol,
            request.mode,
            request.profile,
        ),
        media_type="text/event-stream"
    )

@app.get("/sessions")
async def get_sessions():
    if db is None: return []
    cursor = db.agent_sessions.find().sort("updated_at", -1)
    sessions = await cursor.to_list(length=50)
    return sessions

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    if db is None: return {"error": "DB not found"}
    session = await db.agent_sessions.find_one({"_id": session_id})
    return session or {"error": "Not Found"}

@app.post("/sessions")
async def create_session():
    new_id = str(uuid.uuid4())
    if db is not None:
        await db.agent_sessions.insert_one({
            "_id": new_id,
            "title": "New Chat",
            "preview": "",
            "messages": [],
            "created_at": _now_utc(),
            "updated_at": _now_utc(),
        })
    return {"id": new_id}

# --- RAG ENDPOINTS ---
import tempfile
import shutil

@app.post("/upload_doc")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document, process it, and add to the RAG vector database."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Process and add to ChromaDB
        doc_id = file.filename.replace('.pdf', '') + '_' + str(uuid.uuid4())[:8]
        success, chunk_count = process_pdf(tmp_path, doc_id)
        
        # Cleanup temp file
        os.remove(tmp_path)
        
        if success:
            return {"status": "success", "message": f"Processed {chunk_count} chunks from {file.filename}", "doc_id": doc_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to process PDF.")
    except Exception as e:
        print(f"[RAG Upload Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_rag")
async def clear_rag():
    """Clear all documents from the RAG vector database."""
    try:
        clear_rag_db()
        return {"status": "success", "message": "RAG database cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))