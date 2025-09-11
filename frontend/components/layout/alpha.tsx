import Link from 'next/link'

export function Alpha() {
  return (
    <div className="text-sm">
      <div className="flex gap-2 px-6">
        <div className="flex items-center bg-blue-200 px-2 text-xs font-medium tracking-wider uppercase">
          Alpha
        </div>
        <p>
          This is a new service. Help us improve it and{' '}
          <Link
            href="https://surveys.publishing.service.gov.uk/s/MAQMR1/"
            className="a inline text-blue-600 underline underline-offset-1 hover:text-blue-800 hover:decoration-3 active:bg-yellow-400 active:text-black"
            target="_blank"
            rel="noopener noreferrer"
          >
            give your feedback.
          </Link>
        </p>
      </div>
    </div>
  )
}
