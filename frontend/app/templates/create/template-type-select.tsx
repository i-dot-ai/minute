'use client'

import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { TemplateType } from '@/lib/client'
import { cn } from '@/lib/utils'
import { FileSpreadsheet, FileType } from 'lucide-react'
export const TemplateTypeSelect = ({
  value,
  onChange,
}: {
  value: TemplateType | undefined
  onChange: (v: TemplateType) => void
}) => (
  <RadioGroup
    onValueChange={onChange}
    value={value}
    className="mb-2 grid grid-cols-2 gap-4"
  >
    <Label
      className={cn('flex items-center gap-2 rounded border p-4 text-lg', {
        'border-blue-300 bg-blue-50': value == 'document',
      })}
    >
      <RadioGroupItem value="document" id="document-item" />
      <div className="block w-full">
        <FileType size={50} />
        Document
        <div className="text-muted-foreground text-sm font-normal">
          Design how your minutes should look.
        </div>
      </div>
    </Label>
    <Label
      className={cn('flex items-center gap-2 rounded border p-4 text-lg', {
        'border-blue-300 bg-blue-50': value == 'form',
      })}
    >
      <RadioGroupItem value="form" id="form-item" />
      <div>
        <FileSpreadsheet size={50} />
        Form
        <div className="text-muted-foreground text-sm font-normal">
          For complex question-answer type summarisation.
        </div>
      </div>
    </Label>
  </RadioGroup>
)
