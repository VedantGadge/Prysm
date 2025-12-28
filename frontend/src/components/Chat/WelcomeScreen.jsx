import { useDispatch } from 'react-redux'
import { Briefcase, Search, TrendingUp, BarChart2 } from 'lucide-react'
import { sendMessage } from '../../store/slices/chatSlice'

function WelcomeScreen() {
  const dispatch = useDispatch()

  const suggestions = [
    {
      icon: BarChart2,
      title: 'Chart',
      description: 'Generate a candlestick/line chart and explain the trend for a stock.',
      query: 'Generate a candlestick chart for ICICIBANK and explain the last 3 months trend and key support/resistance levels.',
      mode: 'stock',
      profile: 'balanced',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    {
      icon: TrendingUp,
      title: 'Risk Gauge',
      description: 'Get a risk score with reasons (beta, debt, margins).',
      query: 'Show a risk gauge for RELIANCE and explain what drives the risk score in simple terms.',
      mode: 'stock',
      profile: 'strategic',
      color: 'text-green-400',
      bgColor: 'bg-primary-500/10',
    },
    {
      icon: Search,
      title: 'Compare',
      description: 'Compare two stocks side-by-side on key metrics.',
      query: 'Compare TCS vs INFY on price, market cap, P/E, ROE, net margin, growth, and debt. Summarize which looks stronger and why.',
      mode: 'stock',
      profile: 'balanced',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
    {
      icon: Briefcase,
      title: 'Ask a PDF',
      description: 'Upload a PDF (annual report) and ask questions from it.',
      query: 'I uploaded a PDF. Pull the key risks, guidance, and important numbers from it and give me a short investment summary.',
      mode: 'overall',
      profile: 'strategic',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
  ]

  const handleSuggestionClick = (query) => {
    const suggestion = suggestions.find((s) => s.query === query)
    dispatch(sendMessage({
      message: query,
      stockSymbol: null,
      mode: suggestion?.mode,
      profile: suggestion?.profile,
    }))
  }

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8">
      <div className="max-w-3xl w-full space-y-8">
        {/* Title */}
        <div className="text-center">
          <h1 className="text-xl text-dark-300 font-normal">
            Get started by asking a question or choosing a suggestion below
          </h1>
        </div>

        {/* Suggestion Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {suggestions.map((suggestion, index) => {
            const Icon = suggestion.icon
            return (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion.query)}
                className="flex flex-col gap-3 p-4 bg-dark-800/50 hover:bg-dark-800 border border-dark-700 rounded-xl text-left transition-all hover:border-dark-600 group"
              >
                <div className={`w-10 h-10 ${suggestion.bgColor} rounded-lg flex items-center justify-center`}>
                  <Icon size={20} className={suggestion.color} />
                </div>
                <div>
                  <h3 className="font-medium text-dark-200 mb-1">{suggestion.title}</h3>
                  <p className="text-sm text-dark-400 line-clamp-2">{suggestion.description}</p>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default WelcomeScreen
