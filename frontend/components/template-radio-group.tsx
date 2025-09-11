'use client'

import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { TemplateMetadata } from '@/lib/client'

export const TemplateSelect = ({
  value,
  onChange,
  templates,
  isLoading,
}: {
  value: string
  onChange: (value: string) => void
  templates: TemplateMetadata[]
  isLoading: boolean
}) => {
  return (
    <RadioGroup
      value={value}
      onValueChange={onChange}
      className="mb-2 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {isLoading ? (
        <div className="text-muted-foreground col-span-full text-center">
          Loading templates...
        </div>
      ) : (
        templates.map((option) => (
          <Label
            key={option.name}
            className="flex items-center gap-2 rounded border p-4 has-checked:border-blue-300 has-checked:bg-blue-50 has-checked:text-blue-800"
          >
            <RadioGroupItem
              value={option.name}
              id={option.name}
              className="bg-fill-100"
            />
            <div className="min-h- block w-full">
              {option.name}
              <div className="mt-1 w-full text-xs font-normal">
                {option.description}
              </div>
            </div>
          </Label>
        ))
      )}
    </RadioGroup>
  )
}
