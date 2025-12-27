import { useRef, useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import WelcomeScreen from './WelcomeScreen'

function ChatContainer() {
  const dispatch = useDispatch()
  const { messages, isStreaming, error } = useSelector((state) => state.chat)
  const { selectedStock } = useSelector((state) => state.stock)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <WelcomeScreen />
        ) : (
          <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="max-w-4xl mx-auto px-4 pb-2 w-full">
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-dark-800 bg-dark-900/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <ChatInput disabled={isStreaming} />
        </div>
      </div>
    </div>
  )
}

export default ChatContainer
