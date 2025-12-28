import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Clock,
  Plus,
  MessageSquare,
  ChevronLeft,
  MoreHorizontal
} from 'lucide-react'
import { loadSessions, createNewSession, selectSession } from '../../store/slices/chatSlice'

function Sidebar({ isOpen, onToggle }) {
  const dispatch = useDispatch()
  const { sessionList, currentSessionId } = useSelector((state) => state.chat)

  useEffect(() => {
    dispatch(loadSessions())
  }, [dispatch])

  const handleNewChat = () => {
    dispatch(createNewSession())
  }

  const handleSelectSession = (sessionId) => {
    dispatch(selectSession(sessionId))
  }

  if (!isOpen) return null

  return (
    <aside className="w-64 bg-dark-900 border-r border-dark-700 flex flex-col flex-shrink-0 h-full">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-dark-700 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="font-semibold text-dark-100">Prysm</span>
          <span className="px-1.5 py-0.5 bg-primary-500/20 text-primary-400 text-xs rounded font-medium">
            Pro
          </span>
        </div>
        <button
          onClick={onToggle}
          className="p-1.5 hover:bg-dark-800 rounded-lg transition-colors"
          aria-label="Close sidebar"
        >
          <ChevronLeft size={18} className="text-dark-400" />
        </button>
      </div>

      {/* Actions */}
      <div className="p-3 space-y-2">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-700 rounded-lg transition-colors group"
        >
          <Plus size={18} className="text-dark-400 group-hover:text-primary-400" />
          <span className="text-sm text-dark-300 group-hover:text-dark-100">New Chat</span>
        </button>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <div className="mb-2">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <Clock size={14} className="text-dark-500" />
            <span className="text-xs font-medium text-dark-500 uppercase tracking-wider">Recent</span>
          </div>
        </div>

        <div className="space-y-1">
          {sessionList.map((chat) => (
            <button
              key={chat.id || chat._id}
              onClick={() => handleSelectSession(chat.id || chat._id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors group text-left ${currentSessionId === (chat.id || chat._id)
                ? 'bg-dark-800 border border-dark-700 text-dark-100'
                : 'hover:bg-dark-800 text-dark-300'
                }`}
            >
              <MessageSquare size={16} className={`flex-shrink-0 ${currentSessionId === (chat.id || chat._id) ? 'text-primary-400' : 'text-dark-500'}`} />
              <div className="flex-1 min-w-0">
                <div className="truncate font-medium">{chat.title || 'New Chat'}</div>
                {chat.preview && (
                  <div className="truncate text-xs text-dark-500">{chat.preview}</div>
                )}
              </div>
              <MoreHorizontal
                size={14}
                className="text-dark-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
              />
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-dark-700">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-medium text-sm">
            V
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-dark-200 truncate">User</p>
            <p className="text-xs text-dark-500 truncate">Free Plan</p>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
