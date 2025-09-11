import Link from 'next/link'

export const Footer = () => (
  <footer className="h-[50px] w-full bg-black px-4 py-2 text-white">
    <div className="mx-auto max-w-7xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <nav className="flex gap-6">
            <Link href="/privacy" target="_blank">
              Privacy
            </Link>
            <Link href="/support" target="_blank">
              Support
            </Link>
          </nav>
        </div>
      </div>
    </div>
  </footer>
)
