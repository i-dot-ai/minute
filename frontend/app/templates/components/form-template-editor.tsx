'use client'

import { TemplateData } from '@/types/templates'
import { ArrowDown, ArrowUp, Plus } from 'lucide-react'
import { useFieldArray, useFormContext } from 'react-hook-form'

export const FormTemplateEditor = () => {
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
    <>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--s" htmlFor="styleGuide">
          Style guide
        </label>
        <div id="styleGuide-hint" className="govuk-hint">
          the &ldquo;Style guide&rdquo; to provide style guidance that will
          apply every question.
        </div>
        <textarea
          className="govuk-textarea bg-white"
          id="styleGuide"
          rows={10}
          {...form.register('styleGuide')}
          aria-describedby="styleGuide-hint"
        />
      </div>
      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--s" htmlFor="questions">
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
            <li
              key={field.id}
              className="govuk-!-padding-4 govuk-!-margin-top-6 border-l-4 border-(--govuk-brand-colour) bg-[#d2e2f1]"
            >
              <div className="govuk-!-margin-bottom-4 flex flex-col gap-2 sm:flex-row sm:items-center">
                <div className="govuk-form-group flex-1">
                  <label
                    className="govuk-label"
                    htmlFor={`questions.${index}.title`}
                  >
                    Question text
                  </label>
                  <input
                    className="govuk-input bg-white"
                    id={`questions.${index}.title`}
                    type="text"
                    {...form.register(`questions.${index}.title`)}
                  />
                </div>
                <ul className="govuk-summary-card__actions flex-1">
                  <li className="govuk-summary-card__action">
                    <button
                      type="button"
                      disabled={index === 0}
                      className="govuk-button govuk-button--tertiary govuk-!-margin-0"
                      onClick={() => {
                        fieldArray.swap(index, index - 1)
                      }}
                    >
                      <ArrowUp className="size-4" />{' '}
                      <span className="govuk-visually-hidden">
                        Move up question {index + 1}
                      </span>
                    </button>
                  </li>
                  <li className="govuk-summary-card__action">
                    <button
                      type="button"
                      className="govuk-button govuk-button--tertiary govuk-!-margin-0"
                      disabled={index === array.length - 1}
                      onClick={() => {
                        fieldArray.swap(index + 1, index)
                      }}
                    >
                      <ArrowDown className="size-4" />{' '}
                      <span className="govuk-visually-hidden">
                        Move down question {index + 1}
                      </span>
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
                      Delete{' '}
                      <span className="govuk-visually-hidden">
                        question {index + 1}
                      </span>
                    </button>
                  </li>
                </ul>
              </div>
              <div className="govuk-form-group">
                <label
                  className="govuk-label"
                  htmlFor={`questions.${index}.description`}
                >
                  Question description
                </label>
                <div id="questions-description-hint" className="govuk-hint">
                  A description of how to answer the question, what information
                  to include, and style guidance.
                </div>
                <textarea
                  className="govuk-textarea govuk-!-margin-bottom-0 bg-white"
                  id={`questions.${index}.description`}
                  rows={3}
                  {...form.register(`questions.${index}.description`)}
                  aria-describedby="questions-description-hint"
                ></textarea>
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
    </>
  )
}
