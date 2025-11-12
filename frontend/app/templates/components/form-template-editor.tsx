'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { TemplateData } from '@/types/templates'
import { ArrowDown, ArrowUp, Save, Trash } from 'lucide-react'
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
      <div className="flex gap-2">
        <Button type="submit">
          <Save />
          Save
        </Button>
        <div className="flex-1 text-xs text-red-600">
          <p>
            {form.formState.errors.questions?.root?.message
              ? form.formState.errors.questions?.root?.message
              : null}
          </p>
          <p>
            {form.formState.errors.name?.message
              ? form.formState.errors.name?.message
              : null}
          </p>
          <p>
            {form.formState.errors.description?.message
              ? form.formState.errors.description?.message
              : null}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-4 rounded-lg border p-4">
        <div>
          <h4 className="font-semibold">Template details</h4>
          <p className="text-muted-foreground text-sm">
            Add a name and description so you can find your template later. Name
            and description are not used to generate your minute, any structure
            and style instructions should be added to the template content
            field.
          </p>
        </div>
        <div>
          <Label htmlFor="name">Template Name</Label>
          <Input
            {...form.register('name', {
              required: { value: true, message: 'Name required' },
            })}
            className="mt-2"
            placeholder="Name your template"
          />
        </div>
        <div>
          <Label htmlFor="name">Description</Label>
          <Textarea
            {...form.register('description', {
              required: { value: true, message: 'Description required' },
            })}
            className="mt-2"
            placeholder="A description to help identify the template."
          />
        </div>
      </div>
      <div className="flex flex-col gap-4 rounded-lg border p-4">
        <div className="mb-4">
          <h4 className="font-semibold">Template content</h4>
          <p className="text-muted-foreground text-sm">
            Add questions that you would like to be answered based on the
            transcript, for each question you can provide a description of how
            to answer that question including any style guidance specific to
            that question. Use the &ldquo;Style guide&rdquo; to provide style
            guidance that will apply every question.
          </p>
        </div>
        <div>
          <Label>Style guide</Label>
          <Textarea
            {...form.register('content')}
            className="mt-2"
            placeholder="Enter any guidance that should be followed throughout the whole form."
          />
        </div>
        <div>
          <Label className="mb-2">Questions</Label>
          {fieldArray.fields.map((field, index, array) => (
            <div
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
            </div>
          ))}
          <Button
            type="button"
            onClick={() =>
              fieldArray.append({
                title: '',
                description: '',
                position: form.watch('questions')?.length || 0,
              })
            }
          >
            Add question
          </Button>
        </div>
      </div>
    </form>
  )
}
