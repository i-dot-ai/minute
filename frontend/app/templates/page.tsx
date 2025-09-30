import { UserTemplatesList } from '@/app/templates/components/user-templates-list'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import Link from 'next/link'

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
          <Button asChild>
            <Link href="/templates/new">
              <Plus /> New
            </Link>
          </Button>
        </div>
        <p className="text-muted-foreground">
          Create templates that you can use when generating a Minute.
        </p>
      </header>
      <UserTemplatesList />
    </div>
  )
}
