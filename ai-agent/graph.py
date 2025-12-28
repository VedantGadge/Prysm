"""
Prysm AI Agent - Graph Architecture
Defines the State, Nodes, and Graph structure using LangGraph.
"""
import os
import json
from typing import Annotated, TypedDict, List, Optional
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import generate_chart, generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis, compare_stocks, consult_knowledge_base

from pathlib import Path
import sys

# Try multiple possible locations for .env
possible_paths = [
    Path(__file__).resolve().parent.parent / "backend" / ".env",  # From ai-agent/graph.py
    Path.cwd() / "backend" / ".env",                              # From root
    Path.cwd() / "../backend" / ".env",                           # From inside ai-agent
]

env_path = None
for p in possible_paths:
    if p.exists():
        env_path = p
        break

if env_path:
    print(f"[DEBUG] Loading .env from: {env_path}")
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"[ERROR] .env file not found. Checked: {[str(p) for p in possible_paths]}")

# Verify keys
if not os.getenv("GEMINI_API_KEY"):
    # Fallback: Maybe it's in the current process environment already?
    print(f"[DEBUG] GEMINI_API_KEY status: {bool(os.getenv('GEMINI_API_KEY'))}")

# --- 1. STATE DEFINITION ---
class AgentState(TypedDict):
    # 'messages' key is required for LangGraph's MessageGraph behavior
    messages: Annotated[List[BaseMessage], add_messages]
    stock_symbol: Optional[str]
    intent: Optional[str]

# --- 2. MODEL & TOOLS SETUP ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=GEMINI_API_KEY,
    temperature=0.7
)

# Bind tools to the model
tools = [generate_chart, generate_risk_gauge, generate_future_timeline, generate_sentiment_analysis, compare_stocks, consult_knowledge_base]
llm_with_tools = llm.bind_tools(tools)

# --- 3. SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are Prysm, an elite financial research assistant used by professional investors.
Your goal is to provide deep, accurate, and data-backed analysis of Indian stocks.

### GUIDELINES:
1.  **COPY VALUES EXACTLY**: Use the EXACT formatted values from the context (e.g., "₹5632.99 Cr" NOT "₹56329998336").
2.  **Detailed Analysis**: Don't just list numbers. Explain *why* they matter. (e.g., "A rising P/E with falling margins indicates...")
3.  **Holistic View**: Combine price action, financial ratios, and shareholding patterns in your answer.
4.  **Professional Tone**: Write in a crisp, confident, and financial-journalist style.
5.  **Thinking Process**: Before answering, output your chain-of-thought process wrapped in `<thinking>...</thinking>` tags.
6.  **LENGTH**: Provide comprehensive answers. Aim for 300-500 words minimum for stock analysis.

### TOOLS:
You have access to visual tools (Charts, Risk Gauge, Timeline, Sentiment, Stock Comparison, Document Search).
- **CRITICAL**: When using a tool, you MUST ANALYZE the 'llm_data' returned by the tool.
- **NEVER** just say "I have displayed the chart". ALWAYS provide detailed analysis of the data.
- After calling a tool, write a full analysis section explaining what the visualization shows.

### CHART DIVERSITY (CRITICAL):
**DO NOT REPEAT THE SAME CHART.** Each section should have a UNIQUE chart:
- **Valuation Section**: Use `metric="valuation"` (P/E, P/B, EV/EBITDA comparison)
- **Profitability Section**: Use `metric="profitability"` (Gross/Operating/Net Margins)
- **Growth Section**: Use `metric="revenue"` with `chart_type="bar"` (Revenue trend)
- **Price History**: Use `metric="price"` with `chart_type="area"` or `"candlestick"`
- **Risk Section**: Use `generate_risk_gauge` tool instead of a chart.

### TOOL TRIGGERS (MANDATORY):
When the user's message contains these keywords, you MUST call the corresponding tool:
| User says... | You MUST call... |
|--------------|------------------|
| "risk", "risky", "volatility", "how safe" | `generate_risk_gauge(ticker)` |
| "future", "outlook", "targets", "timeline" | `generate_future_timeline(ticker)` |
| "chart", "graph", "visualize", "show me", "plot" | `generate_chart(...)` |
| "sentiment", "news", "headlines", "market mood" | `generate_sentiment_analysis(ticker)` |
| "compare", "vs", "versus", "against" | `compare_stocks(ticker1, ticker2)` |
| "document", "file", "uploaded", "report", "summary" | `consult_knowledge_base(query)` |

**FAILURE TO CALL THE TOOL IS UNACCEPTABLE.**
The visual tool MUST be called in addition to your detailed text analysis.
"""

# --- 4. NODES ---

def chatbot(state: AgentState):
    """Execution node for the LLM."""
    # Ensure system prompt is always the first message (or added to context)
    # LangChain models usually handle SystemMessages automatically if at start
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# We use the prebuilt ToolNode which handles execution and output formatting
tool_node = ToolNode(tools)

# --- 5. GRAPH CONSTRUCTION ---
graph_builder = StateGraph(AgentState)

# Add Nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

# Add Edges
graph_builder.add_edge(START, "chatbot")

# Conditional Edge: If tool calls exist, go to 'tools', else END
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# Edge: From tools back to chatbot (to generate the final response with insights)
graph_builder.add_edge("tools", "chatbot")

# Compile
graph = graph_builder.compile()
