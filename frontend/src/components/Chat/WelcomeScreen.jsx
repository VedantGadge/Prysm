import { useDispatch } from 'react-redux'
import { Briefcase, Search, TrendingUp, BarChart2 } from 'lucide-react'
import { sendMessage } from '../../store/slices/chatSlice'

function WelcomeScreen() {
  const dispatch = useDispatch()

  const suggestions = [
    {
      icon: Briefcase,
      title: 'Portfolio',
      description: 'How should I adjust my portfolio considering the recent Fed rate cut and its impact on emerging...',
      query: 'How should I adjust my portfolio considering the recent Fed rate cut and its impact on emerging markets?',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    {
      icon: Briefcase,
      title: 'Portfolio',
      description: "What sectors in my portfolio might benefit from India's new trade agreements with New Zealand?",
      query: "What sectors in my portfolio might benefit from India's new trade agreements with New Zealand?",
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    {
      icon: Search,
      title: 'Screener',
      description: 'Screen for stocks in the insurance sector with rising institutional ownership amid market...',
      query: 'Screen for stocks in the insurance sector with rising institutional ownership amid market volatility',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
    {
      icon: Search,
      title: 'Screener',
      description: 'Identify IT companies with recent deal wins and improving margins as global demand rebounds.',
      query: 'Identify IT companies with recent deal wins and improving margins as global demand rebounds',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
  ]

  const handleSuggestionClick = (query) => {
    dispatch(sendMessage({ message: query, stockSymbol: null }))
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
