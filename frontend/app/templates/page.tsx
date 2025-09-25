import { UserTemplatesList } from '@/app/templates/components/user-templates-list'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import Link from 'next/link'

export default function TemplatesPage() {
  return (
    <div>
      <div className="flex justify-between">
        <h1 className="mb-6 text-3xl font-bold">Your templates</h1>
        <Button asChild>
          <Link href="/templates/new">
            <Plus /> New
          </Link>
        </Button>
      </div>
      <UserTemplatesList />
    </div>
  )
}
