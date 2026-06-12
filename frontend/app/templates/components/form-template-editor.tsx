'use client'

import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import { exampleFormTemplates } from '@/app/templates/data/example-templates'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { TemplateData } from '@/types/templates'
import { ArrowDown, ArrowUp, Plus, Save, Trash } from 'lucide-react'
import { useFieldArray, useFormContext } from 'react-hook-form'

export const FormTemplateEditor = ({
  onSubmit,
}: {
  onSubmit: (data: TemplateData) => void
}) => {
  const form = useFormContext<TemplateData>()
  const fieldArray = useFieldArray({
    control: form.control,
    name: 'questions',
    rules: {
      minLength: { value: 1, message: 'Must have at least one question.' },
      required: { value: true, message: 'Must have at least one question.' },
    },
  })
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <div className="govuk-button-group">
        <button type="submit" className="govuk-button">
          <Save className="size-4" />
          Save
        </button>
        <ExampleTemplatesDialog
          examples={exampleFormTemplates}
          onSelectTemplate={(template) => form.reset(template)}
        />
      </div>
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
      <h2 className="govuk-heading-l">Template details</h2>
      <p className="govuk-body">
        Add a name and description so you can find your template later. Name
        and description are not used to generate your minute, any structure
        and style instructions should be added to the template content
        field.
      </p>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="name">
          Template name
        </label>
        <input className="govuk-input" id="name" type="text" {...form.register('name')} />
      </div>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="description">
          Description
        </label>
        <div id="description-hint" className="govuk-hint">
          A description to help identify the template.
        </div>
        <textarea
          className="govuk-textarea"
          id="description"
          {...form.register('description', {
            required: { value: true, message: 'Description required' },
          })}
          aria-describedby="description-hint"
        />
      </div>
      <h2 className="govuk-heading-l">Template content</h2>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="content">
          Style guide
        </label>
        <div id="content-hint" className="govuk-hint">
          the &ldquo;Style guide&rdquo; to provide style
          guidance that will apply every question.
        </div>
        <textarea
          className="govuk-textarea"
          id="content"
          {...form.register('content')}
          aria-describedby="content-hint"
        />
      </div>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="questions">
          Questions
        </label>
        <div id="questions-hint" className="govuk-hint">
          Add questions that you would like to be answered based on the
          transcript, for each question you can provide a description of how
          to answer that question including any style guidance specific to
          that question.
        </div>
        <ul className="govuk-list">

          {fieldArray.fields.map((field, index, array) => (
            <li
              key={field.id}
              className="mb-4 flex gap-1 rounded-md border p-2"
            >
              <div className="flex min-h-full flex-col justify-center gap-1">
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  disabled={index == 0}
                  onClick={() => {
                    fieldArray.swap(index, index - 1)
                  }}
                >
                  <ArrowUp />
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  disabled={index == array.length - 1}
                  onClick={() => {
                    fieldArray.swap(index, index + 1)
                  }}
                >
                  <ArrowDown />
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  onClick={() => {
                    fieldArray.remove(index)
                  }}
                >
                  <Trash />
                </Button>
              </div>
              <div className="flex-1">
                <div className="text-muted-foreground mb-2 rounded text-xs">
                  Question {index + 1}
                </div>
                <Textarea
                  {...form.register(`questions.${index}.title`)}
                  placeholder="Question text"
                  className="min-h-none mb-2"
                  rows={1}
                />
                <Textarea
                  {...form.register(`questions.${index}.description`)}
                  rows={3}
                  placeholder="(optional) Description of how to answer the question, what information to include, and style guidance."
                />
              </div>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="govuk-button govuk-button--secondary"
          onClick={() =>
            fieldArray.append({
              title: '',
              description: '',
              position: form.watch('questions')?.length || 0,
            })
          }
        >
          <Plus className="size-4" /> Add question
        </button>
      </div>
    </form >
  )
}
