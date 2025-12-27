import { useState, useRef, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Send, Paperclip, Mic, ChevronDown, TrendingUp, Building2 } from 'lucide-react'
import { sendMessage } from '../../store/slices/chatSlice'
import { selectStock } from '../../store/slices/stockSlice'
import StockSelectorDropdown from '../StockSelector/StockSelectorDropdown'

function ChatInput({ disabled }) {
  const dispatch = useDispatch()
  const { selectedStock, popularStocks } = useSelector((state) => state.stock)
  const { isStreaming } = useSelector((state) => state.chat)
  const [input, setInput] = useState('')
  const [showStockSelector, setShowStockSelector] = useState(false)
  const [selectedMode, setSelectedMode] = useState('overall')
  const textareaRef = useRef(null)
  const stockSelectorRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`
    }
  }, [input])

  // Close stock selector on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (stockSelectorRef.current && !stockSelectorRef.current.contains(event.target)) {
        setShowStockSelector(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || disabled || isStreaming) return

    dispatch(sendMessage({ 
      message: input.trim(), 
      stockSymbol: selectedStock?.symbol || null 
    }))
    setInput('')
    
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleStockSelect = (stock) => {
    dispatch(selectStock(stock))
    setShowStockSelector(false)
  }

  return (
    <div className="space-y-3">
      {/* Input Container */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="bg-dark-800 border border-dark-700 rounded-xl overflow-hidden focus-within:border-dark-600 transition-colors">
          {/* Text Input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your portfolio, tell your stock screening idea or select a stock"
            disabled={disabled || isStreaming}
            className="w-full bg-transparent text-dark-100 placeholder-dark-500 px-4 pt-4 pb-2 text-sm focus:outline-none resize-none min-h-[48px] max-h-[150px]"
            rows={1}
          />

          {/* Bottom Bar */}
          <div className="flex items-center justify-between px-3 py-2 border-t border-dark-700/50">
            {/* Left Side - Mode Selector and Stock */}
            <div className="flex items-center gap-2">
              {/* Mode Dropdown */}
              <button
                type="button"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
              >
                <span className="text-sm text-dark-300">{selectedMode === 'overall' ? 'Overall' : selectedMode}</span>
                <ChevronDown size={14} className="text-dark-400" />
              </button>

              {/* Stock Selector */}
              <div className="relative" ref={stockSelectorRef}>
                <button
                  type="button"
                  onClick={() => setShowStockSelector(!showStockSelector)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                    selectedStock 
                      ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30' 
                      : 'bg-dark-700 hover:bg-dark-600 text-dark-300'
                  }`}
                >
                  <Building2 size={14} />
                  <span className="text-sm">
                    {selectedStock ? selectedStock.symbol : 'Select Stock'}
                  </span>
                  <ChevronDown size={14} />
                </button>

                {showStockSelector && (
                  <StockSelectorDropdown 
                    onSelect={handleStockSelect}
                    onClose={() => setShowStockSelector(false)}
                  />
                )}
              </div>
            </div>

            {/* Right Side - Actions */}
            <div className="flex items-center gap-2">
              {/* Mode Tags */}
              <div className="hidden sm:flex items-center gap-2">
                <button
                  type="button"
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-primary-500/20 text-primary-400 rounded-lg text-xs font-medium"
                >
                  <TrendingUp size={12} />
                  Strategic
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-xs font-medium"
                >
                  ⚖️ Balanced
                </button>
              </div>

              {/* Send Button */}
              <button
                type="submit"
                disabled={!input.trim() || disabled || isStreaming}
                className={`p-2 rounded-lg transition-all ${
                  input.trim() && !disabled && !isStreaming
                    ? 'bg-primary-500 hover:bg-primary-600 text-white'
                    : 'bg-dark-700 text-dark-500 cursor-not-allowed'
                }`}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}

export default ChatInput
