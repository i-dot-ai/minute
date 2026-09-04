import {
  getTemplatesTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { Template } from '@/types/templates'
import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

/**
 * Resolves the user's default template (if any) into a `Template` the
 * generate flows can pre-select. `is_default` is computed server-side and
 * returned on both template lists, so we find it there rather than matching
 * against the user's `default_template_id`/`default_template_name` by hand.
 *
 * User templates are represented with `agenda_usage: 'not_used'` to match how
 * `TemplateSelect` builds them. Returns `undefined` when no default is set so
 * callers can keep their existing fallback (the "General" template).
 */
export const useDefaultTemplate = (): Template | undefined => {
  const { data: systemTemplates = [] } = useQuery(
    getTemplatesTemplatesGetOptions()
  )
  const { data: userTemplates = [] } = useQuery(
    getUserTemplatesUserTemplatesGetOptions()
  )

  return useMemo(() => {
    const userDefault = userTemplates.find((t) => t.is_default)
    if (userDefault) {
      return {
        id: userDefault.id,
        name: userDefault.name,
        description: userDefault.description,
        agenda_usage: 'not_used',
      }
    }

    const systemDefault = systemTemplates.find((t) => t.is_default)
    if (systemDefault) {
      return {
        id: null,
        name: systemDefault.name,
        description: systemDefault.description,
        agenda_usage: systemDefault.agenda_usage,
      }
    }

    return undefined
  }, [systemTemplates, userTemplates])
}
