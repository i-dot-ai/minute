import type { TemplateMetadata } from '@/lib/client/types.gen'

export const templates = [
  {
    "name": "Cabinet",
    "description": "Formal minutes following cabinet meeting structure",
    "category": "Formal Minutes",
    "agenda_usage": "optional",
    "is_default": false
  },
  {
    "name": "Care Assessment V2",
    "description": "Enhanced Social care assessment template based on Care Act Eligibility Criteria",
    "category": "Social Care",
    "agenda_usage": "not_used",
    "is_default": false
  },
  {
    "name": "Delivery",
    "description": "Formal minutes following the delivery style guide",
    "category": "Formal Minutes",
    "agenda_usage": "not_used",
    "is_default": false
  },
  {
    "name": "Short 'n' Sweet",
    "description": "Executive summary of the meeting + action items",
    "category": "Common",
    "agenda_usage": "not_used",
    "is_default": false
  },
  {
    "name": "General",
    "description": "Standard meeting summary with key points, decisions, and action items",
    "category": "Common",
    "agenda_usage": "optional",
    "is_default": false
  },
  {
    "name": "Planning Committee",
    "description": "Planning committee minutes template",
    "category": "Formal Minutes",
    "agenda_usage": "required",
    "is_default": false
  }
] satisfies Array<TemplateMetadata>
