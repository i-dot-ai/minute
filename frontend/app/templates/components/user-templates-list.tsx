'use client'

import { ExampleTemplatesDialog } from '@/app/templates/components/example-templates-dialog'
import {
  exampleDocumentTemplates,
  exampleFormTemplates,
} from '@/app/templates/data/example-templates'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { TemplateResponse } from '@/lib/client'
import {
  deleteUserTemplateUserTemplatesTemplateIdDeleteMutation,
  duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation,
  getUserTemplatesUserTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Copy,
  Edit,
  FileSpreadsheet,
  FileType,
  FileWarning,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useMemo } from 'react'

export const UserTemplatesList = () => {
  const {
    data: templates = [],
    isLoading,
    isError,
  } = useQuery(getUserTemplatesUserTemplatesGetOptions())
  const [documentTemplates, formTemplates] = useMemo(() => {
    const docs = []
    const forms = []
    for (const template of templates) {
      if (template.type == 'document') {
        docs.push(template)
      } else {
        forms.push(template)
      }
    }
    return [docs, forms]
  }, [templates])
  const router = useRouter()
  if (isLoading) {
    return <Loader2 className="animate-spin" />
  }
  if (isError) {
    return (
      <div>
        <FileWarning />
        <p>Something went wrong fetching your templates</p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-2">
        <div className="flex items-center gap-4">
          <h3 className="flex items-center gap-1 text-xl font-bold">
            <FileType />
            Document
          </h3>
        </div>
        <p className="text-muted-foreground">
          Customise the style and style your minutes.
        </p>
      </div>
      <div className="mb-6 grid auto-rows-fr gap-4 md:grid-cols-2 lg:grid-cols-3">
        {documentTemplates.map((template) => (
          <TemplateCard template={template} key={template.id} />
        ))}
        <Card>
          <CardContent className="flex h-full min-h-45 flex-col gap-2">
            <Button asChild className="flex-1" variant="outline">
              <Link href="/templates/new?type=document">
                <Plus /> Create a new template
              </Link>
            </Button>
            <ExampleTemplatesDialog
              onSelectTemplate={(example) => {
                router.push(`/templates/new?example=${example.name}`)
              }}
              examples={exampleDocumentTemplates}
            />
          </CardContent>
        </Card>
      </div>
      <div className="mb-2">
        <div className="flex items-center gap-4">
          <h3 className="flex items-center gap-1 text-xl font-bold">
            <FileSpreadsheet /> Form
          </h3>
        </div>
        <p className="text-muted-foreground">
          For complex summarisation of meetings into many questions and answers.
        </p>
      </div>
      <div className="grid auto-rows-fr gap-4 md:grid-cols-2 lg:grid-cols-3">
        {formTemplates.map((template) => (
          <TemplateCard template={template} key={template.id} />
        ))}
        <Card>
          <CardContent className="flex h-full min-h-45 flex-col justify-evenly gap-2">
            <Button asChild className="flex-1" variant="outline">
              <Link href="/templates/new?type=form">
                <Plus /> Create a new template
              </Link>
            </Button>
            <ExampleTemplatesDialog
              onSelectTemplate={(example) => {
                router.push(`/templates/new?example=${example.name}`)
              }}
              examples={exampleFormTemplates}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
const TemplateCard = ({ template }: { template: TemplateResponse }) => {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    ...deleteUserTemplateUserTemplatesTemplateIdDeleteMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
    },
  })
  const duplicationMutation = useMutation({
    ...duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
    },
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1">
          {template.type === 'document' ? <FileType /> : <FileSpreadsheet />}
          {template.name}
        </CardTitle>
        <CardDescription>
          <p className="text-sm text-gray-600">
            Updated {new Date(template.updated_datetime!).toLocaleDateString()}
          </p>
        </CardDescription>
      </CardHeader>
      <CardContent className="prose prose-sm max-w-none flex-1 overflow-hidden text-sm text-gray-700">
        {template.description}
      </CardContent>
      <CardFooter className="gap-2">
        <Button
          variant="outline"
          size="sm"
          asChild
          className="flex items-center gap-1"
        >
          <Link href={`/templates/${template.id}`}>
            <Edit size={14} />
            Edit
          </Link>
        </Button>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => {
                duplicationMutation.mutate({
                  path: { template_id: template.id },
                })
              }}
              variant="outline"
            >
              <Copy />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Make a copy</p>
          </TooltipContent>
        </Tooltip>
        <DeleteConfirmDialog
          template={template}
          onConfirm={() => {
            deleteMutation.mutate({
              path: { template_id: template.id! },
            })
          }}
        />
      </CardFooter>
    </Card>
  )
}

const DeleteConfirmDialog = ({
  template,
  onConfirm,
}: {
  template: TemplateResponse
  onConfirm: () => void
}) => (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <Button
        variant="outline"
        size="sm"
        className="text-red-600 hover:bg-red-50 hover:text-red-700"
      >
        <Trash2 size={14} />
      </Button>
    </AlertDialogTrigger>
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Delete Template</AlertDialogTitle>
        <AlertDialogDescription>
          Are you sure you want to delete &quot;{template.name}
          &quot;? This action cannot be undone.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>Cancel</AlertDialogCancel>
        <AlertDialogAction
          onClick={onConfirm}
          className="bg-red-600 hover:bg-red-700"
        >
          Delete
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
)
