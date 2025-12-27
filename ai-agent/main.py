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
            db = client_mongo.get_database()
            print(f"Connected to MongoDB: {db.name}")
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
    
    for turn in history[-5:]:
        role = turn.get('role', 'user')
        text = turn.get('parts', [{}])[0].get('text', '')[:150]
        history_summary += f"{role}: {text}...\n"
        
        if role == 'user':
            tickers = re.findall(r'\b[A-Z]{2,5}\b', text)
            if tickers: last_stock = tickers[0]
    
    intent_prompt = f"""Extract: {{"stock_symbol": "TICKER" or null, "intent": "risk/chart/future/sentiment/analysis"}}.
If user says "it"/"its"/"this stock", use last stock from history: {last_stock}
History: {history_summary}
Query: "{message}" """
    
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
        
        # Fallback
        if not result.get("stock_symbol") and last_stock:
            if any(w in message.lower() for w in ["it", "its", "this", "that"]):
                result["stock_symbol"] = last_stock
        
        return result
    except:
        if last_stock and any(w in message.lower() for w in ["it", "its", "chart"]):
            return {"stock_symbol": last_stock, "intent": "chart"}
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
    if session_id and db:
        session_data = await db.agent_sessions.find_one({"_id": session_id})
    
    if not session_data:
        session_id = str(uuid.uuid4())
        session_data = {"_id": session_id, "title": "New Chat", "messages": [], "created_at": "now"}
    
    history = session_data.get("messages", [])

    # 2. Intent & Context
    intent_data = await extract_intent(message, history)
    target_symbol = intent_data.get("stock_symbol")
    user_intent = intent_data.get("intent", "analysis")
    
    # Update title if it's new
    if len(history) == 0 and target_symbol:
        session_data["title"] = f"{target_symbol} Analysis"
        if db:
            await db.agent_sessions.replace_one({"_id": session_id}, session_data, upsert=True)

    system_prompt_text = "You are Prysm, a financial AI. Use tools provided."
    if target_symbol:
        data = get_stock_data(target_symbol)
        context = create_stock_context(data)
        system_prompt_text += f"\n\nCONTEXT for {target_symbol}:\n{context}"

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
    if db:
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
    if not db: return []
    cursor = db.agent_sessions.find().sort("created_at", -1)
    sessions = await cursor.to_list(length=50)
    return sessions

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    if not db: return {"error": "DB not found"}
    session = await db.agent_sessions.find_one({"_id": session_id})
    return session or {"error": "Not Found"}

@app.post("/sessions")
async def create_session():
    new_id = str(uuid.uuid4())
    session = {"_id": new_id, "title": "New Chat", "messages": [], "created_at": "now"}
    if db:
        await db.agent_sessions.insert_one(session)
    return session

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
