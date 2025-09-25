'use client'

import { StartTranscriptionSection } from '@/components/audio/start-transcription-section'
import { Button } from '@/components/ui/button'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { cn } from '@/lib/utils'
import { CheckCircle, CloudUpload, FileX, Info } from 'lucide-react'
import Dropzone from 'react-dropzone'
import { Controller, FormProvider } from 'react-hook-form'

export const AudioUploadForm = () => {
  const { isPending, onSubmit, form } = useStartTranscription()
  const file = form.watch('file')
  return (
    <FormProvider {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="mt-6 flex flex-col gap-4"
      >
        <div className="flex items-center gap-2 rounded-md bg-blue-50 p-3 text-sm text-blue-700">
          <Info className="size-4 shrink-0" />
          <p>Maximum file size: 5GB</p>
        </div>
        <Controller
          control={form.control}
          name="file"
          render={({ field: { onChange } }) => (
            <Dropzone
              onDrop={(acceptedFiles) =>
                acceptedFiles.length && onChange(acceptedFiles[0])
              }
              accept={{
                'audio/*': [],
                'video/*': [],
              }}
              multiple={false}
            >
              {({
                getRootProps,
                getInputProps,
                isDragActive,
                isDragReject,
              }) => (
                <section>
                  <div
                    {...getRootProps()}
                    className={cn(
                      'flex h-36 items-center justify-center rounded-xl border border-dashed border-slate-300 p-4',
                      isDragActive &&
                        !isDragReject &&
                        'border-blue-400 bg-blue-200',
                      isDragActive &&
                        isDragReject &&
                        'border-red-400 bg-red-50/50',
                      !isDragActive && 'border-slate-300 bg-white'
                    )}
                  >
                    {!file ? (
                      <div className="flex flex-col items-center gap-2 text-slate-500">
                        <div
                          className={`flex items-center gap-2 ${
                            isDragActive
                              ? isDragReject
                                ? 'text-red-500'
                                : 'text-blue-500'
                              : ''
                          }`}
                        >
                          {isDragActive && isDragReject ? (
                            <FileX size={25} />
                          ) : (
                            <CloudUpload size={25} />
                          )}
                          {isDragActive
                            ? isDragReject
                              ? 'Invalid file type'
                              : 'Drop file to upload'
                            : 'Drag and drop your files here'}
                        </div>
                        {!isDragActive && (
                          <>
                            <div className="text-xs">or</div>
                            <Button className="rounded-l-full rounded-r-full bg-blue-50 text-blue-700 hover:bg-blue-100">
                              Choose a file
                            </Button>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="p-6">
                        <div className="flex items-center gap-2 rounded border p-4 text-sm shadow">
                          <div className="flex h-5 w-5 items-center justify-center text-green-500">
                            <CheckCircle />
                          </div>
                          <div className="text-sm text-slate-500">
                            {file instanceof File ? file.name : 'recording'}
                          </div>
                        </div>
                      </div>
                    )}
                    <input {...getInputProps()} />
                  </div>
                </section>
              )}
            </Dropzone>
          )}
        />
        <StartTranscriptionSection isShowing={!!file} isPending={isPending} />
      </form>
    </FormProvider>
  )
}
