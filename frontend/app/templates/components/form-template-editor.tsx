'use client'

import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import { exampleFormTemplates } from '@/app/templates/data/example-templates'
import { TemplateData } from '@/types/templates'
import { ArrowDown, ArrowUp, Plus, Save } from 'lucide-react'
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
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <div className="govuk-button-group">
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
        Add a name and description so you can find your template later. Name and
        description are not used to generate your minute, any structure and
        style instructions should be added to the template content field.
      </p>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="name">
          Template name
        </label>
        <div id="name-hint" className="govuk-hint">
          A short memorable name to help you find this template later.
        </div>
        <input
          required
          className="govuk-input"
          id="name"
          type="text"
          {...form.register('name', {
            required: { value: true, message: 'Template name required' },
          })}
        />
      </div>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--m" htmlFor="description">
          Description
        </label>
        <div id="description-hint" className="govuk-hint">
          A description to help identify the template, NOT a style guide or
          instructions for the summary.
        </div>
        <input
          className="govuk-input"
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
          the &ldquo;Style guide&rdquo; to provide style guidance that will
          apply every question.
        </div>
        <textarea
          className="govuk-textarea"
          id="content"
          rows={10}
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
          transcript, for each question you can provide a description of how to
          answer that question including any style guidance specific to that
          question.
        </div>
        <ul className="govuk-list govuk-list--spaced">
          {fieldArray.fields.map((field, index, array) => (
            <li key={field.id} className="govuk-summary-card">
              <div>
                <div className="govuk-summary-card__title-wrapper">
                  <h3 className="govuk-summary-card__title">
                    Question {index + 1}
                  </h3>
                  <ul className="govuk-summary-card__actions">
                    <li className="govuk-summary-card__action">
                      <button
                        type="button"
                        disabled={index === 0}
                        className="govuk-button govuk-button--secondary govuk-!-margin-0"
                        onClick={() => {
                          fieldArray.swap(index, index - 1)
                        }}
                      >
                        <ArrowUp className="size-4" /> Move up
                      </button>
                    </li>
                    <li className="govuk-summary-card__action">
                      <button
                        type="button"
                        className="govuk-button govuk-button--secondary govuk-!-margin-0"
                        disabled={index === array.length - 1}
                        onClick={() => {
                          fieldArray.swap(index + 1, index)
                        }}
                      >
                        <ArrowDown className="size-4" /> Move down
                      </button>
                    </li>
                    <li className="govuk-summary-card__action">
                      <button
                        type="button"
                        className="govuk-link link--warning align-sub"
                        onClick={() => {
                          fieldArray.remove(index)
                        }}
                      >
                        Delete
                      </button>
                    </li>
                  </ul>
                </div>
                <div className="govuk-summary-card__content">
                  <div className="govuk-form-group">
                    <label
                      className="govuk-label"
                      htmlFor={`questions.${index}.title`}
                    >
                      Question text
                    </label>
                    <input
                      className="govuk-input"
                      id={`questions.${index}.title`}
                      type="text"
                      {...form.register(`questions.${index}.title`)}
                    />
                  </div>
                  <div className="govuk-form-group">
                    <label
                      className="govuk-label"
                      htmlFor={`questions.${index}.description`}
                    >
                      Question description
                    </label>
                    <div id="questions-description-hint" className="govuk-hint">
                      A description of how to answer the question, what
                      information to include, and style guidance.
                    </div>
                    <textarea
                      className="govuk-textarea"
                      id={`questions.${index}.description`}
                      rows={3}
                      {...form.register(`questions.${index}.description`)}
                      aria-describedby="questions-description-hint"
                    ></textarea>
                  </div>
                </div>
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
      <div className="govuk-button-group">
        <button type="submit" className="govuk-button govuk-button--start">
          <Save />
          Save template
        </button>
      </div>
    </form>
  )
}
