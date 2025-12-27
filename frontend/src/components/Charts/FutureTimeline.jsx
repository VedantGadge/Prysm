import React from 'react'
import { Rocket, Target, Calendar } from 'lucide-react'

const FutureTimeline = ({ data }) => {
    // data: { ticker, events: [{date, title, desc}], targets: {bull, bear} }
    const { ticker, events, targets } = data

    return (
        <div className="rounded-xl border border-dark-700 bg-dark-800/50 p-6 my-4">
            <div className="flex items-center gap-3 mb-6">
                <Rocket size={20} className="text-purple-400" />
                <div>
                    <h3 className="text-lg font-semibold text-white">{ticker} Future Outlook</h3>
                    <p className="text-xs text-dark-400">Strategic Roadmap & Targets</p>
                </div>
            </div>

            <div className="relative border-l-2 border-dark-700 ml-3 space-y-8 pb-4">
                {events.map((event, idx) => (
                    <div key={idx} className="relative pl-8">
                        {/* Dot */}
                        <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-dark-900 border-2 border-primary-500 shadow-[0_0_10px_rgba(14,165,233,0.3)]" />

                        <div className="flex flex-col">
                            <span className="text-xs font-mono text-primary-400 mb-1 flex items-center gap-1">
                                <Calendar size={10} /> {event.date}
                            </span>
                            <h4 className="text-sm font-bold text-white">{event.title}</h4>
                            <p className="text-xs text-dark-300 mt-1 leading-relaxed">{event.desc}</p>
                        </div>
                    </div>
                ))}
            </div>

            {targets && (
                <div className="mt-6 pt-4 border-t border-dark-700/50 grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                        <div className="flex items-center gap-2 mb-1">
                            <Target size={14} className="text-green-500" />
                            <span className="text-xs font-medium text-green-400">Bull Case</span>
                        </div>
                        <span className="text-lg font-bold text-white">{targets.bull}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                        <div className="flex items-center gap-2 mb-1">
                            <Target size={14} className="text-red-500" />
                            <span className="text-xs font-medium text-red-400">Bear Case</span>
                        </div>
                        <span className="text-lg font-bold text-white">{targets.bear}</span>
                    </div>
                </div>
            )}
        </div>
    )
}

export default FutureTimeline
