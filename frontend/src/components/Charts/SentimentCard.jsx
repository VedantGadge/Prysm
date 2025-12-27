import React from 'react'
import { Newspaper, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react'

const SentimentCard = ({ data }) => {
    // data: { ticker, overall, score, articles: [{title, source, sentiment, summary, url}], sources: [] }
    const { ticker, overall, score, articles, sources } = data

    // Color and icon logic based on overall sentiment
    let color = '#eab308' // Yellow for neutral
    let icon = <Minus size={20} className="text-yellow-500" />
    let bgGradient = 'from-yellow-500/10 to-transparent'
    let label = 'Neutral'

    if (overall === 'BULLISH' || score > 60) {
        color = '#22c55e'
        icon = <TrendingUp size={20} className="text-green-500" />
        bgGradient = 'from-green-500/10 to-transparent'
        label = 'Bullish'
    } else if (overall === 'BEARISH' || score < 40) {
        color = '#ef4444'
        icon = <TrendingDown size={20} className="text-red-500" />
        bgGradient = 'from-red-500/10 to-transparent'
        label = 'Bearish'
    }

    // Source badge colors
    const sourceBadgeColor = (source) => {
        if (!source) return 'bg-dark-600 text-dark-300 border-dark-500'
        const s = source.toLowerCase()
        if (s.includes('yahoo')) return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
        if (s.includes('google')) return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
        if (s.includes('moneycontrol')) return 'bg-green-500/20 text-green-400 border-green-500/30'
        if (s.includes('economic times') || s.includes('et')) return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
        if (s.includes('mint') || s.includes('livemint')) return 'bg-teal-500/20 text-teal-400 border-teal-500/30'
        if (s.includes('times of india')) return 'bg-red-500/20 text-red-400 border-red-500/30'
        if (s.includes('investing')) return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
        return 'bg-dark-600 text-dark-300 border-dark-500'
    }

    // Individual sentiment badge
    const sentimentBadge = (sentiment) => {
        if (sentiment === 'BULLISH') return <span className="flex-shrink-0">🟢</span>
        if (sentiment === 'BEARISH') return <span className="flex-shrink-0">🔴</span>
        return <span className="flex-shrink-0">🟡</span>
    }

    return (
        <div className={`rounded-xl border border-dark-700 bg-dark-800/50 p-4 my-4 bg-gradient-to-b ${bgGradient} max-w-full overflow-hidden`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-dark-700/50">
                        <Newspaper size={18} className="text-primary-400" />
                    </div>
                    <div>
                        <h3 className="text-base font-semibold text-white">{ticker} Sentiment Analysis</h3>
                        <p className="text-xs text-dark-400">Aggregated from {sources?.length || 0} sources</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {icon}
                    <span className="text-sm font-medium" style={{ color }}>{label}</span>
                </div>
            </div>

            {/* Score Bar */}
            <div className="mb-4">
                <div className="flex justify-between text-xs text-dark-400 mb-1">
                    <span>Bearish</span>
                    <span className="font-medium text-white">{score}/100</span>
                    <span>Bullish</span>
                </div>
                <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                    <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{
                            width: `${score}%`,
                            background: `linear-gradient(to right, #ef4444, #eab308, #22c55e)`,
                            backgroundSize: '200% 100%',
                            backgroundPosition: `${100 - score}% 0`
                        }}
                    />
                </div>
            </div>

            {/* Articles List - Compact */}
            {articles && articles.length > 0 && (
                <div className="space-y-2">
                    <h4 className="text-xs font-medium text-dark-300 mb-2">Recent Headlines:</h4>
                    {articles.slice(0, 4).map((article, idx) => (
                        <div
                            key={idx}
                            className="p-2 rounded-lg bg-dark-700/30 border border-dark-700/50"
                        >
                            <div className="flex items-start gap-2">
                                {sentimentBadge(article.sentiment)}
                                <div className="flex-1 min-w-0 overflow-hidden">
                                    {/* Title with word wrap */}
                                    <p className="text-sm text-white mb-1 break-words whitespace-normal" style={{ wordBreak: 'break-word' }}>
                                        {article.url ? (
                                            <a
                                                href={article.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="hover:text-primary-400 transition-colors"
                                            >
                                                {article.title}
                                                <ExternalLink size={10} className="inline ml-1 opacity-50" />
                                            </a>
                                        ) : (
                                            article.title
                                        )}
                                    </p>
                                    {/* Source + Summary */}
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className={`text-xs px-1.5 py-0.5 rounded border ${sourceBadgeColor(article.source)}`}>
                                            {article.source}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* No articles fallback */}
            {(!articles || articles.length === 0) && (
                <div className="text-center py-3 text-dark-400 text-sm">
                    No recent news articles found for {ticker}
                </div>
            )}

            {/* Source Footer - Compact */}
            {sources && sources.length > 0 && (
                <div className="mt-3 pt-2 border-t border-dark-700/50 flex flex-wrap gap-1.5">
                    {sources.map((source, idx) => (
                        <span
                            key={idx}
                            className={`text-xs px-1.5 py-0.5 rounded border ${sourceBadgeColor(source)}`}
                        >
                            {source}
                        </span>
                    ))}
                </div>
            )}
        </div>
    )
}

export default SentimentCard
