export function handleModalOpenAutoFocus(
  event: Event,
  onOpenAutoFocus?: (event: Event) => void
) {
  onOpenAutoFocus?.(event)
  if (event.defaultPrevented) return

  event.preventDefault()

  const content = event.currentTarget
  if (!(content instanceof HTMLElement)) return

  const title = content.querySelector<HTMLElement>(
    '[data-slot="dialog-title"], [data-slot="alert-dialog-title"]'
  )
  title?.focus()
}
