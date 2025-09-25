import { AgendaUsage } from '@/lib/client'

export type Template = {
  id: string | null
  name: string
  agenda_usage: AgendaUsage
}
