'use client'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useState } from 'react'

export const DeleteConfirmDialog = ({
  name,
  disabled,
  onConfirm,
}: {
  name: string
  disabled: boolean
  onConfirm: () => void
}) => {
  const [open, setOpen] = useState(false)

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <button
          type="button"
          className={`govuk-link govuk-link--no-underline govuk-!-font-size-16 link--warning hover:cursor-pointer ${disabled ? '!cursor-not-allowed !text-gray-500 opacity-50' : ''}`}
          disabled={disabled}
        >
          Delete
          <span className="govuk-visually-hidden">{name}</span>
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            Delete template
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            Are you sure you want to delete <strong>{name}</strong>? This action
            cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="govuk-button-group sm:justify-end">
          <AlertDialogCancel asChild>
            <button
              type="button"
              className="govuk-button govuk-button--secondary !no-underline"
            >
              Cancel
            </button>
          </AlertDialogCancel>
          <button
            type="button"
            onClick={() => {
              onConfirm()
              setOpen(false)
            }}
            className="govuk-button govuk-button--warning"
          >
            Delete
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
