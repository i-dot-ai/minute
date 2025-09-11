import { cn } from '@/lib/utils'
import { Star } from 'lucide-react'
import { useState } from 'react'

interface RatingProps {
  className?: string
  onChange: (rating: number) => void
  value: number | null
}
export function Rating({ className, onChange, value }: RatingProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null)
  return (
    <div
      className="flex items-center gap-0.5"
      onMouseLeave={() => setHoverValue(null)}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={cn(
            'h-4 w-4 cursor-pointer transition-all duration-150 hover:scale-110',
            star <= (hoverValue || value || 0)
              ? 'fill-black text-black'
              : 'text-gray-300 hover:text-gray-400',
            className
          )}
          onClick={() => onChange(star)}
          onMouseEnter={() => setHoverValue(star)}
        />
      ))}
    </div>
  )
}
