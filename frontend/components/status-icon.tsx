import { Badge } from '@/components/ui/badge'
import { JobStatus } from '@/lib/client'
import { CircleCheckBig, CircleX, Loader2 } from 'lucide-react'

export const StatusBadge = ({
  status,
  className,
}: {
  status: JobStatus
  className?: string
}) => {
  if (['awaiting_start', 'in_progress'].includes(status)) {
    return (
      <Badge variant="outline" className={className}>
        <Loader2 className="animate-spin" />
        <p>Processing</p>
      </Badge>
    )
  }

  if (status == 'completed') {
    return (
      <Badge variant="outline" className={className}>
        <CircleCheckBig />
        <p>Completed</p>
      </Badge>
    )
  }
  if (status == 'failed') {
    return (
      <Badge variant="outline" className={className}>
        <CircleX />
        <p>Failed</p>
      </Badge>
    )
  }
}
