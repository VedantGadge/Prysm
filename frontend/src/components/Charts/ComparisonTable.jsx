
import React from 'react';

const ComparisonTable = ({ data }) => {
    if (!data || !data.data || !data.ticker1 || !data.ticker2) return null;

    const { ticker1, ticker2, data: rows } = data;

    return (
        <div className="my-4 animate-fade-in">
            <div className="bg-dark-800/80 border border-dark-700 rounded-xl overflow-hidden shadow-lg backdrop-blur-sm">
                <div className="grid grid-cols-3 bg-dark-900/50 border-b border-dark-700/50">
                    <div className="p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Metric</div>
                    <div className="p-4 text-sm font-bold text-primary-400 text-center border-l border-dark-700/50">{ticker1}</div>
                    <div className="p-4 text-sm font-bold text-blue-400 text-center border-l border-dark-700/50">{ticker2}</div>
                </div>

                <div className="divide-y divide-dark-700/30">
                    {rows.map((row, idx) => (
                        <div key={idx} className="grid grid-cols-3 hover:bg-white/5 transition-colors">
                            <div className="p-3 text-sm text-dark-300 font-medium pl-4">{row.metric}</div>
                            <div className="p-3 text-sm text-gray-200 text-center border-l border-dark-700/30 font-mono">
                                {row[ticker1]}
                            </div>
                            <div className="p-3 text-sm text-gray-200 text-center border-l border-dark-700/30 font-mono">
                                {row[ticker2]}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ComparisonTable;
