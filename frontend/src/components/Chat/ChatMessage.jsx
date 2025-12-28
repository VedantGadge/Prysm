import { useMemo, useState, useEffect } from 'react'
import { User, Bot, ThumbsUp, ThumbsDown, Copy, RefreshCw, Brain, ChevronDown, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import ChartRenderer from '../Charts/ChartRenderer'
import RiskGauge from '../Charts/RiskGauge'
import FutureTimeline from '../Charts/FutureTimeline'
import SentimentCard from '../Charts/SentimentCard'
import ComparisonTable from '../Charts/ComparisonTable'
import LoadingIndicator from '../UI/LoadingIndicator'

// Helper component for smooth typing effect
function SmoothMarkdown({ content }) {
  const [displayedContent, setDisplayedContent] = useState('')

  useEffect(() => {
    // If content matches, do nothing
    if (content === displayedContent) return

    // If content is much larger (initial load), just show it
    if (content.length > displayedContent.length + 20 && displayedContent.length === 0) {
      setDisplayedContent(content)
      return
    }

    // Otherwise, fast typewriter effect
    const timeout = setTimeout(() => {
      setDisplayedContent(content.slice(0, displayedContent.length + 3)) // Type 3 chars at a time for speed
    }, 10)

    return () => clearTimeout(timeout)
  }, [content, displayedContent])

  // Final failsafe cleanup before rendering
  const cleanContent = (text) => {
    if (!text) return ''
    return text
      .replace(/<thinking\b[^>]*>[\s\S]*?<\/thinking>/gi, '') // Remove thinking tags
      .replace(/<thinking\b[^>]*>/gi, '') // Remove orphaned start tags
      .replace(/<\/thinking>/gi, '') // Remove orphaned end tags
      .replace(/\[(CHART|RISK|TIMELINE|SENTIMENT):\{[\s\S]*?\}\]/g, '') // Remove tool tags
      .replace(/\{"generate_[a-z_]+_response":[\s\S]*?\}/g, '') // Remove tool JSON
      .trim()
  }

  return (
    <div className="markdown-content text-sm leading-7 text-gray-200 font-sans tracking-wide">
      <ReactMarkdown>{cleanContent(displayedContent)}</ReactMarkdown>
    </div>
  )
}

function ChatMessage({ message }) {
  const isUser = message.type === 'user'
  const isLoading = message.isLoading
  const [isThinkingOpen, setIsThinkingOpen] = useState(false)

  // Parse content for charts and thinking process
  const { textParts, charts, thinking } = useMemo(() => {
    if (isUser || !message.content) {
      return { textParts: [message.content || ''], charts: [], thinking: null }
    }

    let content = message.content
    let thinkingContent = null

    // 1. Extract Thinking Process (Case Insensitive, handle attributes)
    // Check for complete tag
    const thinkingMatch = /<thinking\b[^>]*>([\s\S]*?)<\/thinking>/i.exec(content)

    if (thinkingMatch) {
      thinkingContent = thinkingMatch[1].trim()
      content = content.replace(thinkingMatch[0], '').trim()
    } else {
      // Check for start tag only (streaming)
      const startTagMatch = /<thinking\b[^>]*>/i.exec(content)
      const endTagMatch = /<\/thinking>/i.exec(content)

      if (startTagMatch && !endTagMatch) {
        const thinkingStart = startTagMatch.index
        thinkingContent = content.slice(thinkingStart + startTagMatch[0].length).trim()
        content = content.slice(0, thinkingStart).trim()
      } else if (endTagMatch && !startTagMatch) {
        content = content.split(/<\/thinking>/i).pop().trim()
      }
    }

    // 2. Parse Tools from content
    const parts = []
    const foundCharts = []
    const seenChartKeys = new Set()
    let currentIndex = 0

    // Helper to clean text content
    const cleanTextContent = (text) => {
      if (!text) return ''
      let cleaned = text

      // Remove complete tool tags
      cleaned = cleaned.replace(/\[(CHART|RISK|TIMELINE|SENTIMENT|COMPARISON):\{[\s\S]*?\}\]/g, '')

      // Remove leaked tool response JSON (hallucinated or injected)
      // Matches {"generate_..._response": ... }
      cleaned = cleaned.replace(/\{"generate_[a-z_]+_response":[\s\S]*?\}/g, '')
      // Matches single line JSON artifacts like {"result": "..."}
      cleaned = cleaned.replace(/\{"result":\s*"[^"]+"\}/g, '')

      // Remove SSE artifacts
      cleaned = cleaned.replace(/\{"content":\s*"/g, '')
      cleaned = cleaned.replace(/"\}\s*/g, '')
      cleaned = cleaned.replace(/\\n\\n/g, '\n\n')
      cleaned = cleaned.replace(/\\n/g, '\n')

      // Remove orphaned quotes/braces
      cleaned = cleaned.replace(/^[\s\n]*["{}\[\]]+\s*/g, '')
      cleaned = cleaned.replace(/[\s\n]*["{}\[\]]+[\s\n]*$/g, '')
      cleaned = cleaned.replace(/^\s*["{}\[\]]+\s*$/gm, '')
      cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n')

      return cleaned.trim()
    }

    while (currentIndex < content.length) {
      const chartIdx = content.indexOf('[CHART:', currentIndex)
      const riskIdx = content.indexOf('[RISK:', currentIndex)
      const timelineIdx = content.indexOf('[TIMELINE:', currentIndex)
      const sentimentIdx = content.indexOf('[SENTIMENT:', currentIndex)
      const comparisonIdx = content.indexOf('[COMPARISON:', currentIndex)

      const indices = [chartIdx, riskIdx, timelineIdx, sentimentIdx, comparisonIdx].filter(i => i !== -1)

      if (indices.length === 0) {
        const remaining = content.slice(currentIndex)
        const partialTagMatch = /\[(CHART|RISK|TIMELINE|SENTIMENT|COMPARISON):?[\s\S]*$/.exec(remaining)

        if (partialTagMatch && message.isLoading) {
          const cleanText = cleanTextContent(remaining.slice(0, partialTagMatch.index))
          if (cleanText) parts.push({ type: 'text', content: cleanText })
        } else {
          const cleanText = cleanTextContent(remaining)
          if (cleanText) parts.push({ type: 'text', content: cleanText })
        }
        break
      }

      let tagStart = Math.min(...indices)
      let tagType = 'CHART'
      if (tagStart === riskIdx) tagType = 'RISK'
      if (tagStart === timelineIdx) tagType = 'TIMELINE'
      if (tagStart === sentimentIdx) tagType = 'SENTIMENT'
      if (tagStart === comparisonIdx) tagType = 'COMPARISON'

      const prefixLen = tagType.length + 2

      // Push text before the tag
      if (tagStart > currentIndex) {
        const textBefore = cleanTextContent(content.slice(currentIndex, tagStart))
        if (textBefore) parts.push({ type: 'text', content: textBefore })
      }

      // Parse JSON content
      let jsonStart = -1
      let braceCount = 0
      let scanIndex = tagStart + prefixLen
      let jsonEnd = -1

      while (scanIndex < content.length) {
        const char = content[scanIndex]
        if (char === '{') {
          jsonStart = scanIndex
          braceCount = 1
          scanIndex++
          break
        } else if (!/\s/.test(char)) {
          break
        }
        scanIndex++
      }

      if (jsonStart !== -1) {
        while (scanIndex < content.length) {
          const char = content[scanIndex]
          if (char === '{') {
            braceCount++
          } else if (char === '}') {
            braceCount--
            if (braceCount === 0) {
              jsonEnd = scanIndex + 1
              break
            }
          }
          scanIndex++
        }
      }

      let tagEnd = -1
      if (jsonEnd !== -1) {
        let closeScan = jsonEnd
        while (closeScan < content.length) {
          const char = content[closeScan]
          if (char === ']') {
            tagEnd = closeScan + 1
            break
          } else if (!/\s/.test(char)) {
            break
          }
          closeScan++
        }
      }

      if (jsonStart !== -1 && jsonEnd !== -1 && tagEnd !== -1) {
        try {
          const jsonStr = content.slice(jsonStart, jsonEnd)
          const parsedData = JSON.parse(jsonStr)

          if (tagType === 'CHART') {
            const datasetLabel = parsedData.datasets?.[0]?.label || ''
            const chartKey = `${datasetLabel}|${JSON.stringify(parsedData.labels || []).slice(0, 30)}`

            if (seenChartKeys.has(chartKey)) {
              console.log('[DEDUP] Skipping duplicate chart:', datasetLabel)
            } else {
              seenChartKeys.add(chartKey)
              parts.push({ type: 'chart', data: parsedData })
              foundCharts.push(parsedData)
            }
          } else if (tagType === 'RISK') {
            parts.push({ type: 'risk', data: parsedData })
          } else if (tagType === 'TIMELINE') {
            parts.push({ type: 'timeline', data: parsedData })
          } else if (tagType === 'SENTIMENT') {
            parts.push({ type: 'sentiment', data: parsedData })
          } else if (tagType === 'COMPARISON') {
            parts.push({ type: 'comparison', data: parsedData })
          }

          currentIndex = tagEnd
        } catch (e) {
          console.error(`${tagType} JSON parse error:`, e)
          currentIndex = tagEnd
        }
      } else {
        if (message.isLoading) {
          break
        } else {
          currentIndex = tagStart + prefixLen
        }
      }
    }

    return {
      textParts: parts,
      charts: foundCharts,
      thinking: thinkingContent
    }
  }, [message.content, message.isLoading, isUser])

  return (
    <div
      className={`flex gap-4 animate-fade-in ${isUser ? 'flex-row-reverse' : 'flex-row'
        }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${isUser
          ? 'bg-gradient-to-br from-orange-400 to-orange-600'
          : 'bg-dark-700 border border-dark-600'
          }`}
      >
        {isUser ? (
          <span className="text-white text-sm font-medium">V</span>
        ) : (
          <div className="w-4 h-4 rounded-sm bg-primary-500/80 shadow-[0_0_8px_rgba(34,197,94,0.4)]" />
        )}
      </div>

      <div
        className={`flex-1 max-w-[85%] ${isUser ? 'text-right' : 'text-left'}`}
      >
        <div
          className={`inline-block rounded-2xl px-5 py-3.5 shadow-sm transition-all duration-300 ${isUser
            ? 'bg-primary-600 text-white rounded-br-md shadow-primary-900/20'
            : 'bg-dark-800/80 backdrop-blur-sm border border-dark-700/50 text-dark-100 rounded-bl-md shadow-dark-900/30'
            }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed font-medium">{message.content}</p>
          ) : (
            <div className="space-y-4">

              {thinking && (
                <div className="mb-2">
                  <button
                    onClick={() => setIsThinkingOpen(!isThinkingOpen)}
                    className={`flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold transition-all duration-200 border px-2 py-1 rounded-full ${isThinkingOpen
                      ? 'text-primary-400 bg-primary-500/10 border-primary-500/20'
                      : 'text-dark-400 hover:text-dark-200 border-transparent hover:bg-dark-700/50'
                      }`}
                  >
                    <Brain size={12} className={isThinkingOpen ? "animate-pulse" : ""} />
                    <span>Analysis Chain</span>
                    {isThinkingOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </button>

                  <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${isThinkingOpen ? 'grid-rows-[1fr] mt-2' : 'grid-rows-[0fr]'}`}>
                    <div className="overflow-hidden">
                      <div className="p-3 bg-dark-950/50 rounded-lg border border-dark-700/50 shadow-inner">
                        <div className="text-xs font-mono text-dark-300 whitespace-pre-wrap leading-relaxed opacity-80">
                          {thinking}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {textParts.map((part, index) => {
                if (part.type === 'text') {
                  return (
                    <SmoothMarkdown key={index} content={part.content} />
                  )
                }
                if (part.type === 'chart') return (
                  <div key={index} className="animate-text-fade-in py-2" style={{ animationDelay: '200ms' }}>
                    <ChartRenderer chartData={part.data} />
                  </div>
                )
                if (part.type === 'risk') return (
                  <div key={index} className="animate-text-fade-in py-2" style={{ animationDelay: '200ms' }}>
                    <RiskGauge data={part.data} />
                  </div>
                )
                if (part.type === 'timeline') return (
                  <div key={index} className="animate-text-fade-in py-2" style={{ animationDelay: '200ms' }}>
                    <FutureTimeline data={part.data} />
                  </div>
                )
                if (part.type === 'sentiment') return (
                  <div key={index} className="animate-text-fade-in py-2" style={{ animationDelay: '200ms' }}>
                    <SentimentCard data={part.data} />
                  </div>
                )
                if (part.type === 'comparison') return (
                  <div key={index} className="animate-text-fade-in py-2" style={{ animationDelay: '200ms' }}>
                    <ComparisonTable data={part.data} />
                  </div>
                )
                return null
              })}
              {isLoading && (
                <div className="flex items-center gap-1 h-6">
                  <div className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              )}
            </div>
          )}
        </div>

        {!isUser && !isLoading && message.content && (
          <div className="flex items-center gap-2 mt-2 ml-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <button className="p-1.5 hover:bg-dark-800 rounded-lg transition-colors group/btn">
              <ThumbsUp
                size={14}
                className="text-dark-500 group-hover/btn:text-primary-400"
              />
            </button>
            <button className="p-1.5 hover:bg-dark-800 rounded-lg transition-colors group/btn">
              <ThumbsDown
                size={14}
                className="text-dark-500 group-hover/btn:text-red-400"
              />
            </button>
            <button
              className="p-1.5 hover:bg-dark-800 rounded-lg transition-colors group/btn"
              onClick={() => navigator.clipboard.writeText(message.content)}
            >
              <Copy
                size={14}
                className="text-dark-500 group-hover/btn:text-dark-300"
              />
            </button>
            <button className="p-1.5 hover:bg-dark-800 rounded-lg transition-colors group/btn">
              <RefreshCw
                size={14}
                className="text-dark-500 group-hover/btn:text-dark-300"
              />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
