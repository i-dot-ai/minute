'use client'

import { TemplateType } from '@/lib/client'
import {
    editUserTemplateUserTemplatesTemplateIdPatchMutation,
    getUserTemplateUserTemplatesTemplateIdGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import posthog from 'posthog-js'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

type NameDescriptionValues = {
    name: string
    description: string
}

export const TemplateNameDescriptionEditor = ({
    templateId,
    type,
    defaultValues,
    onDone,
}: {
    templateId: string
    type: TemplateType
    defaultValues: NameDescriptionValues
    onDone: () => void
}) => {
    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<NameDescriptionValues>({ defaultValues })

    const queryClient = useQueryClient()
    const { mutate, isPending } = useMutation({
        ...editUserTemplateUserTemplatesTemplateIdPatchMutation(),
        onSuccess: () => {
            toast.success('Changes saved!', { position: 'top-center' })
            queryClient.invalidateQueries({
                queryKey: getUserTemplateUserTemplatesTemplateIdGetQueryKey({
                    path: { template_id: templateId },
                }),
            })
            posthog.capture('template_edited')
            onDone()
        },
    })

    const onSubmit = (data: NameDescriptionValues) => {
        mutate({
            path: { template_id: templateId },
            body: { name: data.name, description: data.description },
        })
    }

    return (
        <form onSubmit={handleSubmit(onSubmit)}>
            <div className="text-red-600">
                <p className="govuk-body">{errors.name?.message ?? null}</p>
                <p className="govuk-body">{errors.description?.message ?? null}</p>
            </div>
            <div className="govuk-form-group">
                <h1 className="govuk-label-wrapper">
                    <label className="govuk-label govuk-label--l" htmlFor="name">
                        Template name
                    </label>
                </h1>
                <input
                    id="name"
                    className="govuk-input govuk-!-width-one-half"
                    {...register('name', {
                        required: { value: true, message: 'Template name required' },
                    })}
                />
            </div>
            <div className="govuk-form-group">
                <span className="govuk-label">Template type (unchangeable)</span>
                <p className="govuk-tag govuk-tag--green govuk-!-margin-bottom-0">
                    {type === 'document' ? 'Summary' : 'Q&A'}
                </p>
            </div>
            <div className="govuk-form-group">
                <label className="govuk-label govuk-label--m" htmlFor="description">
                    Description
                </label>
                <textarea
                    id="description"
                    className="govuk-textarea govuk-!-width-one-half"
                    rows={3}
                    {...register('description', {
                        required: { value: true, message: 'Description required' },
                    })}
                />
            </div>
            <div className="govuk-button-group">
                <button type="submit" className="govuk-button" disabled={isPending}>
                    <Save className="size-4" /> Save
                </button>
                <button
                    type="button"
                    className="govuk-button govuk-button--secondary"
                    onClick={onDone}
                >
                    Cancel
                </button>
            </div>
        </form>
    )
}
