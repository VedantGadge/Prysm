import os
import json
import uuid
import asyncio
import httpx
from typing import Optional, AsyncGenerator, Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# LangGraph & LangChain Imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from graph import graph

# Tool Imports for Auto-Inject
from tools import generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis
from stock_data import get_stock_data, generate_price_history

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
{{"stock_symbol": "ACTUAL_TICKER" or null, "intent": "risk/chart/future/sentiment/analysis/general"}}"""
    
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
    return f"Stock: {quote.get('symbol')}, Price: {quote.get('price')}, PE: {fin.get('trailingPE')}"


class ChatRequest(BaseModel):
    message: str
    stock_symbol: Optional[str] = None
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = []


# --- MAIN RESPONSE STREAM ---
async def generate_response_stream(message: str, session_id: str = None):
    
    # 1. Fetch Session from DB (null-safe)
    session_data = None
    if session_id and db is not None:
        session_data = await db.agent_sessions.find_one({"_id": session_id})
    
    if not session_data:
        session_id = str(uuid.uuid4())
        session_data = {"_id": session_id, "title": "New Chat", "messages": [], "created_at": "now"}
    
    history = session_data.get("messages", [])

    # 2. Intent & Context
    intent_data = await extract_intent(message, history)
    target_symbol = intent_data.get("stock_symbol")
    user_intent = intent_data.get("intent", "analysis")
    
    print(f"[MAIN] Extracted target_symbol: {target_symbol}, intent: {user_intent}")
    
    # Update title if it's new
    if len(history) == 0 and target_symbol:
        session_data["title"] = f"{target_symbol} Analysis"
        if db is not None:
            await db.agent_sessions.replace_one({"_id": session_id}, session_data, upsert=True)

    # Build system prompt with STRONG context enforcement
    if target_symbol:
        data = get_stock_data(target_symbol)
        context = create_stock_context(data)
        system_prompt_text = f"""You are Prysm, an expert financial analyst.

IMPORTANT: The user is asking about {target_symbol}. You MUST analyze {target_symbol}.
Do NOT ask the user for the ticker - it is {target_symbol}.

Stock Data for {target_symbol}:
{context}

Use your tools (generate_chart, generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis) to provide visual insights.
Always provide detailed analysis based on real data."""
    else:
        system_prompt_text = """You are Prysm, an expert financial analyst.
If the user asks about a stock without specifying a ticker, ask them which stock they want to analyze (e.g., "RELIANCE", "TCS", "INFY")."""

    # 3. Message Construction (LangChain format)
    lc_messages = [SystemMessage(content=system_prompt_text)]
    for turn in history[-5:]: 
        if turn['role'] == 'user': lc_messages.append(HumanMessage(content=turn['parts'][0]['text']))
        else: lc_messages.append(AIMessage(content=turn['parts'][0]['text']))
    
    # 4. AUTO-INJECT
    auto_tools = []
    if target_symbol:
        if user_intent == "risk": auto_tools.append(("risk", generate_risk_gauge))
        elif user_intent == "future": auto_tools.append(("future", generate_future_timeline))
        elif user_intent == "sentiment": auto_tools.append(("sentiment", generate_sentiment_analysis))
    
    for _, tool_func in auto_tools:
        res = tool_func.invoke({"ticker": target_symbol})
        if isinstance(res, dict):
            ui = res.get("ui_content", "")
            if ui: yield f"data: {json.dumps({'content': ui})}\n\n"
            summary = res.get("llm_data", {})
            lc_messages.append(SystemMessage(content=f"AUTO-ANALYSIS DATA for {target_symbol}: {json.dumps(summary)}"))

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
    new_messages = [
        {"role": "user", "parts": [{"text": message}]},
        {"role": "model", "parts": [{"text": accumulated_text}]}
    ]
    if db is not None:
        await db.agent_sessions.update_one(
            {"_id": session_id},
            {"$push": {"messages": {"$each": new_messages}}, "$setOnInsert": {"title": "New Chat", "created_at": "now"}},
            upsert=True
        )


# --- API ENDPOINTS ---

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        generate_response_stream(request.message, request.session_id),
        media_type="text/event-stream"
    )

@app.get("/sessions")
async def get_sessions():
    if db is None: return []
    cursor = db.agent_sessions.find().sort("created_at", -1)
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
    session = {"_id": new_id, "id": new_id, "title": "New Chat", "messages": [], "created_at": "now"}
    if db is not None:
        await db.agent_sessions.insert_one(session)
    return session

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
