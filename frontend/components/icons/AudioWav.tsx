export const AudioWav = ({ count = 10 }) => {
  const lineWidth = 4
  const spacing = 12 // Space between lines
  const totalWidth = count * lineWidth + (count - 1) * spacing + 20 // +20 for padding
  const svgHeight = 200

  return (
    <svg width={totalWidth} height="200" xmlns="http://www.w3.org/2000/svg">
      {Array.from({ length: count }, (_, i) => {
        const x = 10 + i * (lineWidth + spacing) + lineWidth / 2
        const minHeight = 20
        const maxHeight = svgHeight - 20
        const randomHeight = Math.random() * (maxHeight - minHeight) + minHeight
        const y1 = (svgHeight - randomHeight) / 2
        const y2 = y1 + randomHeight

        return (
          <line
            stroke="blue"
            key={i}
            x1={x}
            y1={y1}
            x2={x}
            y2={y2}
            strokeWidth={lineWidth}
            strokeLinecap="round"
            className="animate-updown stroke-blue-600"
            style={{ animationDelay: `${(i + 1) * 0.15}s` }}
          />
        )
      })}
    </svg>
  )
}
