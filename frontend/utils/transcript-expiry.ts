export function isExpiringTomorrow(
  createdDatetime: string,
  retentionDays: number | null | undefined
): boolean {
  if (!retentionDays) return false
  const created = new Date(createdDatetime)
  const expiresAt = new Date(created)
  expiresAt.setUTCDate(expiresAt.getUTCDate() + retentionDays)
  const daysUntilExpiry = Math.ceil(
    (expiresAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  )
  return daysUntilExpiry <= 1
}
