import { ReactElement } from 'react'

export default function NewLayout({ children }: { children: ReactElement }) {
  return <div className="mx-auto max-w-3xl pt-1">{children}</div>
}
