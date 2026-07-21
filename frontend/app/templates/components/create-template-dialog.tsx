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

type StartOption = 'blank' | 'example'

export function CreateTemplateDialog() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<'choice' | 'example'>('choice')
  const [choice, setChoice] = useState<StartOption | null>(null)
  const [selectedTemplate, setSelectedTemplate] =
    useState<ExampleTemplate | null>(null)
  const router = useRouter()

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (!isOpen) {
      setStep('choice')
      setChoice(null)
      setSelectedTemplate(null)
    }
  }

  const handleContinue = () => {
    if (choice === 'blank') {
      setOpen(false)
      router.push('/templates/create')
    } else if (choice === 'example') {
      setStep('example')
    }
  }

  const handleUseExample = () => {
    if (!selectedTemplate) return
    posthog.capture('template_example_selected', {
      example_name: selectedTemplate.name,
    })
    setOpen(false)
    router.push(`/templates/create?example=${selectedTemplate.id}`)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild type="button">
        <button className="govuk-button">Create new template</button>
      </DialogTrigger>
      <DialogContent wideModal={step === 'example'}>
        {step === 'choice' ? (
          <>
            <div className="govuk-form-group govuk-!-padding-bottom-0">
              <fieldset className="govuk-fieldset">
                <legend className="govuk-fieldset__legend govuk-fieldset__legend--l">
                  <DialogTitle className="govuk-fieldset__heading">
                    Create new template
                  </DialogTitle>
                </legend>
                <div
                  className="govuk-radios govuk-radios--small govuk-!-margin-top-6"
                  data-module="govuk-radios"
                >
                  <div className="govuk-radios__item">
                    <input
                      className="govuk-radios__input"
                      id="start-option-blank"
                      name="start-option"
                      type="radio"
                      value="blank"
                      checked={choice === 'blank'}
                      onChange={() => setChoice('blank')}
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
                  <div className="govuk-radios__item">
                    <input
                      className="govuk-radios__input"
                      id="start-option-example"
                      name="start-option"
                      type="radio"
                      value="example"
                      checked={choice === 'example'}
                      onChange={() => setChoice('example')}
                    />
                    <label
                      className="govuk-label govuk-radios__label"
                      htmlFor="start-option-example"
                    >
                      <h2 className="govuk-heading-s govuk-!-margin-bottom-2">
                        Start from an example
                      </h2>
                      <p className="govuk-body-s">
                        Choose an example template to customise.
                      </p>
                    </label>
                  </div>
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
                  disabled={!choice}
                  onClick={handleContinue}
                >
                  Continue
                </button>
              </div>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="govuk-form-group">
              <fieldset className="govuk-fieldset">
                <legend className="govuk-fieldset__legend govuk-fieldset__legend--l">
                  <DialogTitle className="govuk-fieldset__heading">
                    Choose an example template
                  </DialogTitle>
                </legend>
                <div
                  className="govuk-radios govuk-!-margin-top-9 flex flex-wrap"
                  data-module="govuk-radios"
                >
                  {allExampleTemplates.map((template) => (
                    <div
                      className="govuk-radios__item new-recording__radio-item md:w-1/2"
                      key={template.id}
                    >
                      <input
                        className="govuk-radios__input"
                        id={`example-template-${template.id}`}
                        name="example-template"
                        type="radio"
                        value={template.id}
                        checked={selectedTemplate?.id === template.id}
                        onChange={() => setSelectedTemplate(template)}
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor={`example-template-${template.id}`}
                      >
                        <div className="govuk-!-margin-bottom-2 flex items-center gap-2">
                          <h2 className="govuk-heading-s govuk-!-margin-bottom-0">
                            {template.name}
                          </h2>
                          <span className="govuk-tag govuk-tag--green">
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
                  onClick={() => setStep('choice')}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="govuk-button"
                  disabled={!selectedTemplate}
                  onClick={handleUseExample}
                >
                  Use example
                </button>
              </div>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
