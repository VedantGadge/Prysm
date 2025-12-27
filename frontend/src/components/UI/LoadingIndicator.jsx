function LoadingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      <div className="w-2 h-2 bg-primary-400 rounded-full loading-dot" />
      <div className="w-2 h-2 bg-primary-400 rounded-full loading-dot" />
      <div className="w-2 h-2 bg-primary-400 rounded-full loading-dot" />
    </div>
  )
}

export default LoadingIndicator
