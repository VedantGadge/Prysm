import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts'

// Color palette for charts
const COLORS = [
  '#22c55e', // Green
  '#3b82f6', // Blue
  '#a855f7', // Purple
  '#f97316', // Orange
  '#ec4899', // Pink
  '#14b8a6', // Teal
]

// Custom tooltip styling for dark theme
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    // Format values with appropriate units
    const formatValue = (value, name) => {
      if (typeof value !== 'number') return value

      // Check if it's a large monetary value (Market Cap, Revenue, etc.)
      const monetaryLabels = ['Revenue', 'Profit', 'Cash', 'Debt', 'EBITDA', 'Balance', 'Cash Flow']
      const isMonetary = monetaryLabels.some(l => name?.includes(l))

      if (isMonetary || value > 1000000) {
        // Format as Crores for Indian context
        if (value >= 10000000) {
          return `₹${(value / 10000000).toFixed(2)} Cr`
        } else if (value >= 100000) {
          return `₹${(value / 100000).toFixed(2)} L`
        }
        return `₹${value.toLocaleString()}`
      }

      // Percentage values
      const percentLabels = ['Margin', 'ROE', 'ROA', '%', 'Growth']
      const isPercent = percentLabels.some(l => name?.includes(l))
      if (isPercent) {
        return `${value.toFixed(2)}%`
      }

      return value.toLocaleString()
    }

    return (
      <div className="bg-dark-800 border border-dark-600 rounded-lg p-3 shadow-lg">
        <p className="text-dark-200 text-sm font-medium mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {formatValue(entry.value, entry.name)}
          </p>
        ))}
      </div>
    )
  }
  return null
}

function ChartRenderer({ chartData }) {
  if (!chartData || !chartData.type) {
    return null
  }

  const { type, title, data } = chartData

  // Transform Chart.js format to Recharts format
  const transformData = () => {
    if (!data || !data.labels) return []
    return data.labels.map((label, index) => {
      const point = { name: label }
      data.datasets?.forEach((dataset, dsIndex) => {
        const key = dataset.label || `value${dsIndex}`
        point[key] = dataset.data?.[index] ?? 0
      })
      return point
    })
  }

  // Transform data for pie charts
  const transformPieData = () => {
    if (!data || !data.labels) return []
    const dataset = data.datasets?.[0]
    if (!dataset) return []
    return data.labels.map((label, index) => ({
      name: label,
      value: dataset.data?.[index] ?? 0,
    }))
  }

  // Transform data for candlestick
  const transformCandleData = () => {
    if (!data || !data.datasets) return []
    const rawData = data.datasets[0].data
    return data.labels.map((label, index) => {
      const [open, high, low, close] = rawData[index] || [0, 0, 0, 0]
      return {
        name: label,
        open, high, low, close,
        color: close >= open ? '#22c55e' : '#ef4444'
      }
    })
  }

  // Transform for Radar
  const transformRadarData = () => {
    if (!data || !data.labels) return []
    // Radar expects data array where Key is category (label)
    // But Recharts Radar expects: [{ subject: 'Math', A: 120, B: 110 }, ...]
    // Our 'labels' are the subjects (Valuation, Growth etc)
    return data.labels.map((label, index) => {
      const point = { subject: label }
      data.datasets?.forEach((ds) => {
        point[ds.label] = ds.data[index]
      })
      return point
    })
  }

  const chartDataTransformed = (() => {
    if (type === 'pie' || type === 'doughnut') return transformPieData()
    if (type === 'candlestick') return transformCandleData()
    if (type === 'radar') return transformRadarData()
    return transformData()
  })()

  const datasetLabels = data?.datasets?.map(ds => ds.label) || ['Value']

  const renderChart = () => {
    switch (type) {
      case 'line':
      case 'area':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartDataTransformed} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                {datasetLabels.map((label, index) => (
                  <linearGradient key={index} id={`gradient-${index}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => v.toLocaleString()} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {datasetLabels.map((label, index) => (
                <Area
                  key={index}
                  type="monotone"
                  dataKey={label}
                  stroke={COLORS[index % COLORS.length]}
                  fill={type === 'area' ? `url(#gradient-${index})` : 'transparent'}
                  strokeWidth={2}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'radar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartDataTransformed}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b' }} />
              {datasetLabels.map((label, index) => (
                <Radar
                  key={index}
                  name={label}
                  dataKey={label}
                  stroke={COLORS[index % COLORS.length]}
                  fill={COLORS[index % COLORS.length]}
                  fillOpacity={0.4}
                />
              ))}
              <Legend />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        )

      case 'candlestick':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartDataTransformed}>
              <XAxis dataKey="name" stroke="#64748b" />
              <YAxis domain={['auto', 'auto']} stroke="#64748b" />
              <Tooltip />
              <Bar dataKey="close" name="Close Price">
                {chartDataTransformed.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartDataTransformed} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => v.toLocaleString()} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {datasetLabels.map((label, index) => (
                <Bar key={index} dataKey={label} fill={COLORS[index % COLORS.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'horizontal_bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartDataTransformed} layout="vertical" margin={{ top: 10, right: 30, left: 60, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} width={80} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {datasetLabels.map((label, index) => (
                <Bar key={index} dataKey={label} fill={COLORS[index % COLORS.length]} radius={[0, 4, 4, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'pie':
      case 'doughnut':
        const innerRadius = type === 'doughnut' ? 60 : 0
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartDataTransformed}
                cx="50%"
                cy="50%"
                innerRadius={innerRadius}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                labelLine={{ stroke: '#64748b' }}
              >
                {chartDataTransformed.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#0f172a" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )

      default:
        return (
          <div className="text-dark-400 text-center py-8">
            Unsupported chart type: {type}
          </div>
        )
    }
  }

  return (
    <div className="chart-container my-4">
      {title && (
        <h4 className="text-sm font-semibold text-dark-200 mb-3">{title}</h4>
      )}
      <div className="bg-dark-800/50 rounded-lg p-4">
        {renderChart()}
      </div>
    </div>
  )
}

export default ChartRenderer
