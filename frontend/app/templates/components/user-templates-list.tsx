'use client'

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
  FileText,
  FileType,
  FileWarning,
  Loader2,
  Trash2,
} from 'lucide-react'
import Link from 'next/link'

export const UserTemplatesList = () => {
  const {
    data: templates = [],
    isLoading,
    isError,
  } = useQuery(getUserTemplatesUserTemplatesGetOptions())
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

  if (!templates.length) {
    return (
      <div className="text-muted-foreground flex h-full w-full flex-col items-center justify-center gap-2">
        <FileText size="8rem" />
        <p>Create your own templates to customise your minutes.</p>
      </div>
    )
  }
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {templates.map((template) => (
        <Card key={template.id}>
          <CardHeader>
            <CardTitle className="flex items-center gap-1">
              {template.type === 'document' ? (
                <FileType />
              ) : (
                <FileSpreadsheet />
              )}
              {template.name}
            </CardTitle>
            <CardDescription>
              <p className="text-sm text-gray-600">
                Updated{' '}
                {new Date(template.updated_datetime!).toLocaleDateString()}
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
                      path: { template_id: template.id! },
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
      ))}
    </div>
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
