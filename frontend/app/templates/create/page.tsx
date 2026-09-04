'use client'

import { DocumentTemplateEditor } from '@/app/templates/components/document-template-editor'
import { FormTemplateEditor } from '@/app/templates/components/form-template-editor'
import { allExampleTemplates } from '@/app/templates/data/example-templates'
import { TemplateType } from '@/lib/client'
import { createUserTemplateUserTemplatesPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { TemplateData } from '@/types/templates'
import { useMutation } from '@tanstack/react-query'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { Suspense, useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'

function NewTemplatePageContent() {
  const [newTemplateType, setNewTemplateType] =
    useState<TemplateType>('document')
  const form = useForm<TemplateData>({
    defaultValues: {
      name: '',
      description: '',
      content: '',
      styleGuide: '',
      questions: [],
      type: newTemplateType,
    },
  })
  const navigation = useRouter()
  const searchParams = useSearchParams()
  const exampleId = searchParams.get('example')
  useEffect(() => {
    const example = allExampleTemplates.find((t) => t.id === exampleId)
    if (!example) return
    setNewTemplateType(example.type)
    form.reset({
      name: example.name,
      description: example.description,
      type: example.type,
      questions: example.questions,
      content: example.type === 'form' ? '' : example.content,
      styleGuide: example.type === 'form' ? example.content : '',
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exampleId])
  const { mutateAsync: saveTemplate } = useMutation({
    ...createUserTemplateUserTemplatesPostMutation(),
    onSuccess: () => {
      toast.success('Saved template!')
      posthog.capture('template_created')
      navigation.push('/templates')
    },
  })
  const onSubmit = async (data: TemplateData) => {
    const { styleGuide, ...rest } = data
    await saveTemplate({
      body: {
        ...rest,
        content: data.type === 'form' ? (styleGuide ?? '') : rest.content,
        questions:
          data.type === 'form' && data.questions
            ? data.questions.map((q, i) => ({ ...q, position: i }))
            : null,
      },
    })
  }

  return (
    <FormProvider {...form}>
      <div className="govuk-width-container govuk-!-padding-top-4">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
              <ol className="govuk-breadcrumbs__list">
                <li className="govuk-breadcrumbs__list-item">
                  <Link className="govuk-breadcrumbs__link" href="/templates">
                    Back
                  </Link>
                </li>
              </ol>
            </nav>
            <h1 className="govuk-heading-l">New template</h1>
            <form onSubmit={form.handleSubmit(onSubmit)}>
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
                <label className="govuk-label govuk-label--s" htmlFor="name">
                  Template name
                </label>
                <input
                  required
                  className="govuk-input govuk-!-width-one-half"
                  id="name"
                  type="text"
                  {...form.register('name', {
                    required: {
                      value: true,
                      message: 'Template name required',
                    },
                  })}
                />
              </div>
              <div className="govuk-form-group">
                <label
                  className="govuk-label govuk-label--s"
                  htmlFor="description"
                >
                  Description
                </label>
                <div id="description-hint" className="govuk-hint">
                  What type of meeting is this template used for?
                </div>
                <textarea
                  className="govuk-textarea govuk-!-width-one-half"
                  id="description"
                  {...form.register('description', {
                    required: { value: true, message: 'Description required' },
                  })}
                  aria-describedby="description-hint"
                />
              </div>
              <div className="govuk-form-group">
                <fieldset className="govuk-fieldset">
                  <legend className="govuk-fieldset__legend govuk-fieldset__legend--s">
                    <h2 className="govuk-fieldset__heading">Template type</h2>
                  </legend>
                  <div
                    className="govuk-radios govuk-radios--inline govuk-radios--small govuk-radios--cards"
                    data-module="govuk-radios"
                  >
                    <div className="govuk-radios__item">
                      <input
                        className="govuk-radios__input"
                        id="template-type-document"
                        name="template-type"
                        type="radio"
                        value="document"
                        checked={newTemplateType === 'document'}
                        onChange={() => {
                          setNewTemplateType('document')
                          form.setValue('type', 'document')
                        }}
                        aria-describedby="template-type-document-hint"
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="template-type-document"
                      >
                        <h3 className="govuk-heading-s">Summary</h3>
                        <p className="govuk-body">
                          Provides a summary of the meeting.
                        </p>
                      </label>
                    </div>
                    <div className="govuk-radios__item">
                      <input
                        className="govuk-radios__input"
                        id="template-type-form"
                        name="template-type"
                        type="radio"
                        value="form"
                        checked={newTemplateType === 'form'}
                        onChange={() => {
                          setNewTemplateType('form')
                          form.setValue('type', 'form')
                        }}
                        aria-describedby="template-type-form-hint"
                      />
                      <label
                        className="govuk-label govuk-radios__label"
                        htmlFor="template-type-form"
                      >
                        <h3 className="govuk-heading-s">Q & A</h3>
                        <p className="govuk-body">
                          Answers a list of questions from the meeting.
                        </p>
                      </label>
                    </div>
                  </div>
                </fieldset>
              </div>
              {newTemplateType === 'document' && <DocumentTemplateEditor />}
              {newTemplateType === 'form' && <FormTemplateEditor />}
              <div className="govuk-button-group">
                <button type="submit" className="govuk-button">
                  Save template
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </FormProvider>
  )
}

export default function NewTemplatePage() {
  return (
    <Suspense>
      <NewTemplatePageContent />
    </Suspense>
  )
}
