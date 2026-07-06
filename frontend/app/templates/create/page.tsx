'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
import {
  exampleDocumentTemplates,
  exampleFormTemplates,
} from '@/app/templates/data/example-templates'
import { TemplateType } from '@/lib/client'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { TemplateData } from '@/types/templates'
import { useMutation } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { Suspense, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'

function NewTemplateContent() {
  const searchParams = useSearchParams()
  const [newTemplateType, setNewTemplateType] = useState<TemplateType>('document')
  const templateExampleParam = searchParams.get('example')
  const foundExample = [
    ...exampleDocumentTemplates,
    ...exampleFormTemplates,
  ].find((v) => v.name == templateExampleParam)
  const form = useForm<TemplateData>({
    defaultValues: foundExample
      ? foundExample
      : {
        name: '',
        description: '',
        content: '',
        questions: [],
        type:
          newTemplateType &&
            ['document', 'form'].includes(newTemplateType)
            ? (newTemplateType as TemplateType)
            : undefined,
      },
  })
  const navigation = useRouter()
  const { mutateAsync: saveTemplate } = useMutation({
    ...createUserTemplateUserTemplatesPostMutation(),
    onSuccess: () => {
      toast.success('Saved template!')
      posthog.capture('template_created')
      navigation.push('/templates')
    },
  })
  const onSubmit = async (data: TemplateData) => {
    await saveTemplate({
      body: {
        ...data,
        questions:
          data.type === 'form' && data.questions
            ? data.questions.map((q, i) => ({ ...q, position: i }))
            : null,
      },
    })
  }
  const templateType = form.watch('type')

  return (
    <FormProvider {...form}>
      <div className="govuk-width-container govuk-main-wrapper">
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link className="govuk-breadcrumbs__link" href="/templates">
                Back
              </Link>
            </li>
          </ol>
        </nav>
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <h1 className="govuk-heading-xl">New template</h1>
          </div>
        </div>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-full">
              <div className="text-red-600">
                <p className="govuk-body">
                  {form.formState.errors.questions?.root?.message
                    ? form.formState.errors.questions?.root?.message
                    : null}
                </p>
                <p className="govuk-body">
                  {form.formState.errors.name?.message
                    ? form.formState.errors.name?.message
                    : null}
                </p>
                <p className="govuk-body">
                  {form.formState.errors.description?.message
                    ? form.formState.errors.description?.message
                    : null}
                </p>
              </div>
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="name">
                  Template name
                </label>
                <input
                  required
                  className="govuk-input govuk-!-width-one-half"
                  id="name"
                  type="text"
                  {...form.register('name', {
                    required: { value: true, message: 'Template name required' },
                  })}
                />
              </div>
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="description">
                  Description
                </label>
                <div id="description-hint" className="govuk-hint">
                  What type of meeting is this template used for?
                </div>
                <input
                  className="govuk-input govuk-!-width-one-half"
                  id="description"
                  {...form.register('description', {
                    required: { value: true, message: 'Description required' },
                  })}
                  aria-describedby="description-hint"
                />
              </div>
              <div className="govuk-form-group">
                <fieldset className="govuk-fieldset">
                  <legend className="govuk-fieldset__legend">
                    <h2 className="govuk-fieldset__heading">
                      Template type
                    </h2>
                  </legend>
                  <div className="govuk-radios flex gap-4" data-module="govuk-radios">
                    <div className="govuk-radios__item new-recording__radio-item flex-1">
                      <input
                        className="govuk-radios__input"
                        id="template-type-document"
                        name="template-type"
                        type="radio"
                        value="document"
                        checked={newTemplateType === 'document'}
                        onChange={() => setNewTemplateType('document')}
                        aria-describedby="template-type-document-hint"
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="template-type-document"
                      >
                        <h3 className="govuk-body">
                          Summary template
                        </h3>
                        <p
                          className="govuk-body"
                        >
                          Provides a summary of the meeting.
                        </p>
                      </label>
                    </div>
                    <div className="govuk-radios__item new-recording__radio-item flex-1">
                      <input
                        className="govuk-radios__input"
                        id="template-type-form"
                        name="template-type"
                        type="radio"
                        value="form"
                        checked={newTemplateType === 'form'}
                        onChange={() => setNewTemplateType('form')}
                        aria-describedby="template-type-form-hint"
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="template-type-form"
                      >
                        <h3 className="govuk-body">
                          Q&A template
                        </h3>
                        <p
                          className="govuk-body"
                        >
                          Answers a list of questions from the meeting.
                        </p>
                      </label>
                    </div>
                  </div>
                </fieldset>
              </div>
            </div>
          </div>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-full">
              {newTemplateType === 'document' && (
                <DocumentTemplateEditor />
              )}
              {newTemplateType === 'form' && (
                <FormTemplateEditor />
              )}
              <div className="govuk-button-group">
                <button type="submit" className="govuk-button govuk-button--start">
                  <Save />
                  Save template
                </button>
              </div>
            </div>
          </div>
        </form>
      </div >
    </FormProvider >
  )
}

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <NewTemplateContent />
    </Suspense>
  )
}
