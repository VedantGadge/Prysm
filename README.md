# Prysm - Stock Research Copilot

A chat-based investment research UI where users can ask questions about stocks and receive AI-powered analysis with interactive charts.

![Prysm Screenshot](./screenshot.png)

## Features

- 💬 **Chat Interface** - Clean, modern chat UI with user and AI messages
- 📊 **Interactive Charts** - Line, bar, pie, and horizontal bar charts embedded in responses
- 🤖 **AI-Powered Analysis** - Gemini LLM integration for intelligent stock analysis
- 📈 **Financial Data** - Mock data for Indian stocks (RELIANCE, TCS, INFY, HDFCBANK, etc.)
- 🔄 **Streaming Responses** - Real-time streaming of AI responses
- 🎨 **Dark Theme** - Professional dark mode design

## Tech Stack

- **Frontend**: React.js + Vite + Tailwind CSS
- **State Management**: Redux Toolkit
- **Backend API**: Node.js + Express
- **AI Agent**: FastAPI + Google Gemini
- **Charts**: Chart.js + react-chartjs-2

## Project Structure

```
prysm/
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── store/        # Redux store
│   │   └── services/     # API services
│   └── package.json
├── backend/           # Node.js Express backend
│   ├── src/
│   │   ├── routes/       # API routes
│   │   └── services/     # Business logic
│   └── package.json
├── ai-agent/          # FastAPI AI agent
│   ├── main.py          # FastAPI app
│   ├── stock_data.py    # Mock stock data
│   └── requirements.txt
└── package.json       # Root package.json
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.9+
- npm or yarn

### Installation

1. **Clone and install dependencies:**

```bash
cd prysm

# Install all Node.js dependencies
npm install
cd frontend && npm install && cd ..
cd backend && npm install && cd ..

# Install Python dependencies
cd ai-agent
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cd ..
```

2. **Configure environment variables:**

```bash
# Backend
cp backend/.env.example backend/.env

# AI Agent
cp ai-agent/.env.example ai-agent/.env
```

3. **Add your Gemini API key:**

Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

Edit `ai-agent/.env`:
```
GEMINI_API_KEY=your_actual_api_key_here
```

### Running the Application

**Option 1: Run each service separately (recommended for development)**

Terminal 1 - Frontend:
```bash
cd frontend
npm run dev
```

Terminal 2 - Backend:
```bash
cd backend
npm run dev
```

Terminal 3 - AI Agent:
```bash
cd ai-agent
# Activate virtual environment first
python -m uvicorn main:app --reload --port 8001
```

**Option 2: Run all services together**

```bash
npm run dev
```

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- AI Agent: http://localhost:8001

## Usage

### Example Queries

1. **Price Trends**
   - "Show INFY price trend for last 1 year"
   - "What's the price history of RELIANCE?"

2. **Financial Analysis**
   - "Explain TCS revenue breakup"
   - "Show me quarterly financials for HDFC Bank"

3. **Comparisons**
   - "Compare P/E ratios of IT stocks"
   - "Compare RELIANCE and TCS"

4. **Financial Health**
   - "How strong is HDFC Bank financially?"
   - "Analyze Infosys financial ratios"

5. **Shareholding**
   - "What's the shareholding pattern of RELIANCE?"
   - "Show promoter holding in TCS"

### Available Stocks

- RELIANCE (Reliance Industries)
- TCS (Tata Consultancy Services)
- INFY (Infosys)
- HDFCBANK (HDFC Bank)
- ICICIBANK (ICICI Bank)
- WIPRO (Wipro)
- BHARTIARTL (Bharti Airtel)
- ITC
- SBIN (State Bank of India)
- KOTAKBANK (Kotak Mahindra Bank)

## API Endpoints

### Backend (Express)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to AI (streaming) |
| GET | `/api/stock/:symbol` | Get stock data |
| GET | `/api/stock/search?q=query` | Search stocks |
| GET | `/api/health` | Health check |

### AI Agent (FastAPI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Chat with AI (streaming) |
| GET | `/health` | Health check |

## Chart Format

The AI includes charts in responses using this format:

```json
[CHART:{"type":"bar","title":"Revenue Comparison","data":{"labels":["Q1","Q2","Q3","Q4"],"datasets":[{"label":"Revenue","data":[100,120,130,150]}]}}]
```

Supported chart types:
- `line` - Price trends, time series
- `bar` - Category comparisons
- `horizontal_bar` - P/E ratios, rankings
- `pie` - Shareholding patterns
- `doughnut` - Composition breakdowns

## Development

### Frontend Development

```bash
cd frontend
npm run dev     # Start dev server
npm run build   # Production build
npm run lint    # Run ESLint
```

### Backend Development

```bash
cd backend
npm run dev     # Start with nodemon
npm start       # Production start
```

### AI Agent Development

```bash
cd ai-agent
python -m uvicorn main:app --reload --port 8001
```

## Configuration

### Environment Variables

**Backend (.env)**
```
PORT=8000
AI_AGENT_URL=http://localhost:8001
```

**AI Agent (.env)**
```
GEMINI_API_KEY=your_api_key_here
HOST=0.0.0.0
PORT=8001
```

## Notes

- The app works without a Gemini API key using mock responses
- Stock data is mocked for demonstration purposes
- In production, integrate with real financial data APIs (Yahoo Finance, etc.)

## License

MIT
