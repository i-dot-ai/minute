'use client'

import type { RoleName } from '@/lib/client/types.gen'
import { X } from 'lucide-react'

export const RolePill = ({ role }: { role: RoleName }) => (
  <span className="govuk-tag govuk-tag--blue govuk-!-margin-right-1 govuk-!-margin-bottom-1 inline-flex items-center">
    {role}
  </span>
)

export const RemovableRolePill = ({
  role,
  onRemove,
  disabled,
}: {
  role: RoleName
  onRemove: () => void
  disabled?: boolean
}) => (
  <span className="govuk-tag govuk-tag--blue govuk-!-margin-right-1 govuk-!-margin-bottom-1 inline-flex items-center gap-1">
    {role}
    <button
      type="button"
      aria-label={`Remove ${role} role`}
      className="inline-flex cursor-pointer items-center border-0 bg-transparent p-0 text-current disabled:cursor-not-allowed disabled:opacity-50"
      onClick={onRemove}
      disabled={disabled}
    >
      <X className="size-3" aria-hidden="true" />
    </button>
  </span>
)
