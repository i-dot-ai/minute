'use client'

import {
  allExampleTemplates,
  ExampleTemplate,
} from '@/app/templates/data/example-templates'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useState } from 'react'

type Selection =
  | { type: 'blank' }
  | { type: 'example'; template: ExampleTemplate }

export function CreateTemplateDialog() {
  const [open, setOpen] = useState(false)
  const [selection, setSelection] = useState<Selection | null>(null)
  const router = useRouter()

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (!isOpen) {
      setSelection(null)
    }
  }

  const handleContinue = () => {
    if (!selection) return
    if (selection.type === 'blank') {
      setOpen(false)
      router.push('/templates/create')
      return
    }
    posthog.capture('template_example_selected', {
      example_name: selection.template.name,
    })
    setOpen(false)
    router.push(`/templates/create?example=${selection.template.id}`)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild type="button">
        <button className="govuk-button">Create new template</button>
      </DialogTrigger>
      <DialogContent wideModal>
        <div className="govuk-form-group">
          <fieldset className="govuk-fieldset">
            <legend className="govuk-fieldset__legend govuk-fieldset__legend--l">
              <DialogTitle className="govuk-fieldset__heading">
                Create new template
              </DialogTitle>
            </legend>
            <div
              className="govuk-radios govuk-radios--small govuk-!-margin-top-6 flex flex-wrap"
              data-module="govuk-radios"
            >
              <div className="govuk-radios__item new-recording__radio-item w-full">
                <input
                  className="govuk-radios__input"
                  id="start-option-blank"
                  name="start-option"
                  type="radio"
                  value="blank"
                  checked={selection?.type === 'blank'}
                  onChange={() => setSelection({ type: 'blank' })}
                />
                <label
                  className="govuk-label govuk-radios__label"
                  htmlFor="start-option-blank"
                >
                  <h2 className="govuk-heading-s govuk-!-margin-bottom-2">
                    Blank template
                  </h2>
                  <p className="govuk-body-s">
                    Start from scratch with an empty template.
                  </p>
                </label>
              </div>
              {allExampleTemplates.map((template) => (
                <div
                  className="govuk-radios__item new-recording__radio-item md:w-1/2"
                  key={template.id}
                >
                  <input
                    className="govuk-radios__input"
                    id={`start-option-${template.id}`}
                    name="start-option"
                    type="radio"
                    value={template.id}
                    checked={
                      selection?.type === 'example' &&
                      selection.template.id === template.id
                    }
                    onChange={() => setSelection({ type: 'example', template })}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor={`start-option-${template.id}`}
                  >
                    <div className="govuk-!-margin-bottom-2 flex items-center gap-2">
                      <h2 className="govuk-heading-s govuk-!-margin-bottom-0">
                        {template.name}
                      </h2>
                      <span className="govuk-tag govuk-tag--green govuk-!-font-size-16">
                        {template.type === 'document' ? 'Summary' : 'Q&A'}
                      </span>
                    </div>
                    <p className="govuk-body-s">{template.description}</p>
                  </label>
                </div>
              ))}
            </div>
          </fieldset>
        </div>
        <DialogFooter>
          <div className="govuk-button-group flex justify-end">
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="govuk-button"
              disabled={!selection}
              onClick={handleContinue}
            >
              Continue
            </button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
