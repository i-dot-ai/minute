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

export const DeleteConfirmDialog = ({
  name,
  disabled,
  onConfirm,
}: {
  name: string
  disabled: boolean
  onConfirm: () => void
}) => (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <button
        className={`govuk-link link--warning flex items-center gap-2 hover:cursor-pointer ${disabled ? '!cursor-not-allowed !text-gray-500 opacity-50' : ''}`}
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
            className="govuk-link govuk-link--no-visited-state text-(--govuk-link-colour)"
          >
            Cancel
          </button>
        </AlertDialogCancel>
        <button
          type="button"
          onClick={onConfirm}
          className="govuk-link link--warning"
        >
          Delete template
        </button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
)
