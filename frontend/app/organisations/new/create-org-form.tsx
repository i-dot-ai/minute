'use client'

import { createOrgOrganisationsPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { FormEvent, useState } from 'react'

export const CreateOrgForm = () => {
  const router = useRouter()
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { mutate: createOrg, isPending } = useMutation({
    ...createOrgOrganisationsPostMutation(),
    onSuccess: (org) => {
      router.push(`/organisations/${org.id}`)
    },
    onError: () => {
      setError('There is a problem creating the organisation. Try again.')
    },
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Enter an organisation name')
      return
    }
    createOrg({ body: { name: trimmed } })
  }

  return (
    <form onSubmit={submit}>
      <div
        className={`govuk-form-group ${error ? 'govuk-form-group--error' : ''}`}
      >
        <label className="govuk-label govuk-label--m" htmlFor="org-name">
          Organisation name
        </label>
        <div id="org-name-hint" className="govuk-hint">
          The name members will see for this organisation
        </div>
        {error && (
          <p className="govuk-error-message" id="org-name-error">
            <span className="govuk-visually-hidden">Error:</span> {error}
          </p>
        )}
        <input
          className={`govuk-input bg-white ${error ? 'govuk-input--error' : ''}`}
          id="org-name"
          name="org-name"
          type="text"
          maxLength={255}
          value={name}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? 'org-name-error' : 'org-name-hint'}
          onChange={(e) => {
            setName(e.target.value)
            if (error) setError(null)
          }}
        />
      </div>
      <button type="submit" className="govuk-button" disabled={isPending}>
        {isPending && <Loader2 className="size-4 animate-spin" />}
        Create organisation
      </button>
    </form>
  )
}
