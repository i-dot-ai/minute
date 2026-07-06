'use client'

import {
    Dialog,
    DialogContent,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog'
import posthog from 'posthog-js'

import Link from 'next/link'
import { useState } from 'react'
import { Plus } from 'lucide-react'

type TemplateType = 'document' | 'form'

export function NewTemplateDialog() {
    const [open, setOpen] = useState(false)
    const [templateType, setTemplateType] = useState<TemplateType>('document')

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild type="button">
                <button className="govuk-button">
                    <Plus className="size-4" />
                    Create new template
                </button>
            </DialogTrigger>
            <DialogContent>
                <DialogTitle className="govuk-heading-l">
                    Create a new template
                </DialogTitle>
                <fieldset className="govuk-fieldset">
                    <legend className="govuk-fieldset__legend">
                        Which type of template do you want to create?
                    </legend>
                    <div className="govuk-radios" data-module="govuk-radios">
                        <div className="govuk-radios__item">
                            <input
                                className="govuk-radios__input"
                                id="template-type-document"
                                name="template-type"
                                type="radio"
                                value="document"
                                checked={templateType === 'document'}
                                onChange={() => setTemplateType('document')}
                                aria-describedby="template-type-document-hint"
                            />
                            <label
                                className="govuk-label govuk-label--s govuk-radios__label"
                                htmlFor="template-type-document"
                            >
                                Summary template
                            </label>
                            <div
                                className="govuk-hint govuk-radios__hint"
                                id="template-type-document-hint"
                            >
                                Set the style and structure of summary
                            </div>
                        </div>
                        <div className="govuk-radios__item">
                            <input
                                className="govuk-radios__input"
                                id="template-type-form"
                                name="template-type"
                                type="radio"
                                value="form"
                                checked={templateType === 'form'}
                                onChange={() => setTemplateType('form')}
                                aria-describedby="template-type-form-hint"
                            />
                            <label
                                className="govuk-label govuk-label--s govuk-radios__label"
                                htmlFor="template-type-form"
                            >
                                Q&A template
                            </label>
                            <div
                                className="govuk-hint govuk-radios__hint"
                                id="template-type-form-hint"
                            >
                                Set a list of questions that should be answered from the meeting
                            </div>
                        </div>
                    </div>
                </fieldset>
                <div className="govuk-button-group flex justify-end govuk-!-margin-top-6">
                    <button
                        className="govuk-link text-(--govuk-link-colour)"
                        type="button"
                        onClick={() => setOpen(false)}
                    >
                        Cancel
                    </button>
                    <Link
                        className="govuk-button govuk-!-margin-bottom-0"
                        role="button"
                        href={`/templates/new?type=${templateType}`}
                        onClick={() =>
                            posthog.capture('template_create_started', {
                                template_type: templateType,
                            })
                        }
                    >
                        Generate new template
                    </Link>
                </div>
            </DialogContent>
        </Dialog>
    )
}
