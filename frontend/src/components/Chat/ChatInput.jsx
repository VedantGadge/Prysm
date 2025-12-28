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
  const [showModeSelector, setShowModeSelector] = useState(false)
  const [selectedProfile, setSelectedProfile] = useState('strategic')
  const [isListening, setIsListening] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const textareaRef = useRef(null)
  const stockSelectorRef = useRef(null)
  const modeSelectorRef = useRef(null)
  const fileInputRef = useRef(null)
  const recognitionRef = useRef(null)
  const isSpeechSupported = ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window)

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setIsUploading(true)
    try {
      await import('../../services/api').then(m => m.chatAPI.uploadDocument(file))
      setInput(prev => prev + ` [Attached: ${file.name}] Analyze this document.`)
    } catch (err) {
      console.error(err)
      alert("Upload failed")
    } finally {
      setIsUploading(false)
      // Allow re-uploading the same file
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // Speech Recognition (single instance)
  useEffect(() => {
    if (!isSpeechSupported) return

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript
      if (transcript) {
        setInput((prev) => (prev ? prev + ' ' + transcript : transcript))
      }
    }

    recognition.onerror = () => {
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition
    return () => {
      try { recognition.abort() } catch (e) { }
      recognitionRef.current = null
    }
  }, [isSpeechSupported])

  const toggleListening = () => {
    if (!isSpeechSupported) return

    if (!isListening) {
      setIsListening(true)
      try {
        recognitionRef.current?.start()
      } catch (e) {
        setIsListening(false)
      }
      return
    }

    setIsListening(false)
    try {
      recognitionRef.current?.stop()
    } catch (e) {
      // ignore
    }
  }

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
      if (stockSelectorRef.current && !stockSelectorRef.current.contains(event.target)) setShowStockSelector(false)
      if (modeSelectorRef.current && !modeSelectorRef.current.contains(event.target)) setShowModeSelector(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || disabled || isStreaming) return

    dispatch(sendMessage({
      message: input.trim(),
      stockSymbol: selectedStock?.symbol || null,
      mode: selectedMode,
      profile: selectedProfile,
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

  const modeLabel = selectedMode === 'overall' ? 'Overall' : 'Stock'

  return (
    <div className="space-y-3">
      {/* Input Container */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="bg-dark-800 border border-dark-700 rounded-xl overflow-visible focus-within:border-dark-600 transition-colors">
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
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between px-3 py-2 border-t border-dark-700/50">
            {/* Left Side - Mode Selector and Stock */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Attach */}
              <button
                type="button"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || isStreaming || isUploading}
                aria-disabled={disabled || isStreaming || isUploading}
              >
                {isUploading ? <span className="animate-spin">⌛</span> : <Paperclip size={14} className="text-dark-400" />}
                <span className="text-sm text-dark-300">Attach</span>
              </button>

              {/* Mode Dropdown */}
              <div className="relative" ref={modeSelectorRef}>
                <button
                  type="button"
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                  onClick={() => setShowModeSelector((v) => !v)}
                  aria-haspopup="menu"
                  aria-expanded={showModeSelector}
                >
                  <span className="text-sm text-dark-300">{modeLabel}</span>
                  <ChevronDown size={14} className="text-dark-400" />
                </button>

                {showModeSelector && (
                  <div
                    role="menu"
                    className="absolute bottom-full left-0 mb-2 w-44 bg-dark-800 border border-dark-700 rounded-xl shadow-xl z-50 overflow-hidden"
                  >
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setSelectedMode('overall'); setShowModeSelector(false) }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${selectedMode === 'overall' ? 'bg-dark-700 text-dark-100' : 'hover:bg-dark-700 text-dark-300'}`}
                    >
                      Overall
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setSelectedMode('stock'); setShowModeSelector(false) }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${selectedMode === 'stock' ? 'bg-dark-700 text-dark-100' : 'hover:bg-dark-700 text-dark-300'}`}
                    >
                      Stock
                    </button>
                  </div>
                )}
              </div>

              {/* Stock Selector */}
              <div className="relative" ref={stockSelectorRef}>
                <button
                  type="button"
                  onClick={() => setShowStockSelector(!showStockSelector)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${selectedStock
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
            <div className="flex items-center gap-2 justify-between sm:justify-end">
              {/* Mode Tags */}
              <div className="hidden sm:flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedProfile('strategic')}
                  aria-pressed={selectedProfile === 'strategic'}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${selectedProfile === 'strategic' ? 'bg-primary-500/20 text-primary-400' : 'bg-dark-700 text-dark-400 hover:bg-dark-600'}`}
                >
                  <TrendingUp size={12} />
                  Strategic
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedProfile('balanced')}
                  aria-pressed={selectedProfile === 'balanced'}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${selectedProfile === 'balanced' ? 'bg-blue-500/20 text-blue-400' : 'bg-dark-700 text-dark-400 hover:bg-dark-600'}`}
                >
                  ⚖️ Balanced
                </button>
              </div>

              {/* Mic Button */}
              <button
                type="button"
                onClick={toggleListening}
                disabled={!isSpeechSupported || disabled || isStreaming}
                aria-disabled={!isSpeechSupported || disabled || isStreaming}
                className={`p-2 rounded-lg transition-all ${(!isSpeechSupported || disabled || isStreaming)
                  ? 'bg-dark-700 text-dark-500 cursor-not-allowed'
                  : isListening
                  ? 'bg-red-500/20 text-red-400 animate-pulse'
                  : 'bg-dark-700 hover:bg-dark-600 text-dark-300'
                  }`}
                title={isSpeechSupported ? 'Voice Input' : 'Voice input not supported in this browser'}
              >
                <Mic size={18} />
              </button>

              {/* Send Button */}
              <button
                type="submit"
                disabled={!input.trim() || disabled || isStreaming}
                className={`p-2 rounded-lg transition-all ${input.trim() && !disabled && !isStreaming
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

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".pdf"
      />
    </div>
  )
}

export default ChatInput
