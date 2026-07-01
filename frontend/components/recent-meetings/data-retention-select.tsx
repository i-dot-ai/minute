'use client'

import {
  getUserUsersMeGetOptions,
  getUserUsersMeGetQueryKey,
  updateDataRetentionUsersDataRetentionPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export const DataRetentionSelect = () => {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const queryClient = useQueryClient()
  const { mutate: updateDataRetention } = useMutation({
    ...updateDataRetentionUsersDataRetentionPatchMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getUserUsersMeGetQueryKey() })
    },
  })

  return (
    <div className="govuk-form-group">
      <label className="govuk-label" htmlFor="retention-period">
        Retention period
      </label>
      <select
        className="govuk-select"
        id="retention-period"
        aria-describedby="retention-period-hint"
        value={user?.data_retention_days ?? 'indefinitely'}
        onChange={(e) => {
          const value = e.target.value
          updateDataRetention({
            body: {
              data_retention_days:
                value === 'indefinitely' ? null : Number(value),
            },
          })
        }}
      >
        <option value="1">1 day</option>
        <option value="7">7 days</option>
        <option value="30">30 days</option>
        <option value="90">90 days</option>
        <option value="indefinitely">Indefinitely</option>
      </select>
    </div>
  )
}
