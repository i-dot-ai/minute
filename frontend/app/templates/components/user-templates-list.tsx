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
import { Card } from '@/components/ui/card'
import {
  deleteUserTemplateUserTemplatesTemplateIdDeleteMutation,
  getUserTemplatesUserTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Edit, FileText, FileWarning, Loader2, Trash2 } from 'lucide-react'
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
        <Card key={template.id} className="p-4">
          <div className="mb-3 flex items-start justify-between">
            <div className="flex-1">
              <h3 className="mb-1 truncate text-lg font-semibold">
                {template.name}
              </h3>
              <p className="text-sm text-gray-600">
                Created{' '}
                {new Date(template.created_datetime!).toLocaleDateString()}
              </p>
              {template.updated_datetime !== template.created_datetime && (
                <p className="text-sm text-gray-500">
                  Updated{' '}
                  {new Date(template.updated_datetime!).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>

          <div className="mb-4 flex-1">
            <div
              className="prose prose-sm max-w-none overflow-hidden text-sm text-gray-700"
              style={{
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
              }}
            >
              {template.content}
            </div>
          </div>

          <div className="flex items-center gap-2">
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
                    onClick={() =>
                      deleteMutation.mutate({
                        path: { template_id: template.id! },
                      })
                    }
                    className="bg-red-600 hover:bg-red-700"
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </Card>
      ))}
    </div>
  )
}
