import { UserTemplatesList } from '@/app/templates/components/user-templates-list'

export default function TemplatesPage() {
  return (
    <div>
      <header className="mb-6">
        <div className="flex justify-between">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold">Your templates</h1>
            <span className="bg-blue-200 px-2 py-0.5 text-xs font-medium uppercase">
              Experimental
            </span>
          </div>
        </div>
        <p className="text-muted-foreground">
          Use templates to customise the structure and style of your minutes.
        </p>
      </header>
      <UserTemplatesList />
    </div>
  )
}
