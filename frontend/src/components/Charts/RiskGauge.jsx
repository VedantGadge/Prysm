import React from 'react'
import { AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react'

const RiskGauge = ({ data }) => {
    // data: { ticker, score (0-100), level (Low/Mod/High), factors: [] }
    const { ticker, score, level, factors } = data

    // Color logic
    let color = '#22c55e' // Green
    let icon = <CheckCircle size={24} className="text-green-500" />
    let bgGradient = 'from-green-500/10 to-transparent'

    if (score > 40) {
        color = '#eab308' // Yellow
        icon = <AlertTriangle size={24} className="text-yellow-500" />
        bgGradient = 'from-yellow-500/10 to-transparent'
    }
    if (score > 70) {
        color = '#ef4444' // Red
        icon = <ShieldAlert size={24} className="text-red-500" />
        bgGradient = 'from-red-500/10 to-transparent'
    }

    // Semi-circle gauge calculation
    const radius = 80
    const circumference = radius * Math.PI
    const strokeDashoffset = circumference - (score / 100) * circumference

    return (
        <div className={`rounded-xl border border-dark-700 bg-dark-800/50 p-6 my-4 bg-gradient-to-b ${bgGradient}`}>
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-white">{ticker} Risk Assessment</h3>
                    <p className="text-xs text-dark-400">AI-Derived Volatility Score</p>
                </div>
                {icon}
            </div>

            <div className="flex flex-col md:flex-row items-center gap-8">
                {/* Gauge Graphic */}
                <div className="relative w-48 h-32 flex justify-center items-end">
                    <svg
                        className="w-48 h-48"
                        viewBox="0 0 192 120"
                        style={{ overflow: 'visible' }}
                    >
                        {/* Background Arc */}
                        <path
                            d="M 16 100 A 80 80 0 0 1 176 100"
                            fill="transparent"
                            stroke="#334155"
                            strokeWidth="12"
                            strokeLinecap="round"
                        />
                        {/* Filled Arc (Score) */}
                        <path
                            d="M 16 100 A 80 80 0 0 1 176 100"
                            fill="transparent"
                            stroke={color}
                            strokeWidth="12"
                            strokeLinecap="round"
                            strokeDasharray={`${(score / 100) * 251.2} 251.2`}
                            className="transition-all duration-1000 ease-out"
                        />
                    </svg>
                    <div className="absolute bottom-0 flex flex-col items-center">
                        <span className="text-3xl font-bold text-white">{score}</span>
                        <span className="text-xs text-dark-400 font-medium uppercase tracking-wider">{level}</span>
                    </div>
                </div>

                {/* Factors List */}
                <div className="flex-1 w-full">
                    <h4 className="text-sm font-medium text-dark-300 mb-3">Key Risk Factors:</h4>
                    <ul className="space-y-2">
                        {factors.map((factor, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-dark-200">
                                <span className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-1.5 flex-shrink-0" />
                                {factor}
                            </li>
                        ))}
                        {factors.length === 0 && (
                            <li className="text-sm text-dark-500 italic">No major risks detected.</li>
                        )}
                    </ul>
                </div>
            </div>
        </div>
    )
}

export default RiskGauge
