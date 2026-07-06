import {
  AgendaUsage,
  CreateQuestion,
  Question,
  TemplateType,
} from '@/lib/client'

export type Template = {
  id: string | null
  name: string
  description: string
  agenda_usage: AgendaUsage
}

export type TemplateData = {
  name: string
  content: string
  styleGuide?: string
  description: string
  type: TemplateType
  questions: (Question | CreateQuestion)[] | null
}

// View model for a row in the templates table: merges user templates and
// system (default) templates into a single shape.
export type TemplateRowData = {
  id: string | null
  name: string
  description: string
  isSystem: boolean
  format: TemplateType
  is_default: boolean
}
