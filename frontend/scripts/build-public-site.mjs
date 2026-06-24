import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendRoot = join(__dirname, '..')
const dist = join(frontendRoot, 'dist')
const publicSiteRoot = join(frontendRoot, 'public-site')
const contentRoot = join(frontendRoot, 'content')

const pages = [
  {
    title: 'Minute',
    contentPath: join(publicSiteRoot, 'pages/index.html'),
    outputPath: 'index.html',
  },
  {
    title: 'Privacy Notice',
    contentPath: join(contentRoot, 'privacy-page.html'),
    outputPath: 'privacy/index.html',
    wrap: true,
  },
  {
    title: 'Support',
    contentPath: join(contentRoot, 'support-page.html'),
    outputPath: 'support/index.html',
    wrap: true,
  },
]

const headPartial = readFileSync(
  join(publicSiteRoot, 'partials/head.html'),
  'utf8'
)
const headerPartial = readFileSync(
  join(publicSiteRoot, 'partials/header.html'),
  'utf8'
)
const footerPartial = readFileSync(
  join(publicSiteRoot, 'partials/footer.html'),
  'utf8'
)

function wrapContent(html) {
  return `<div class="govuk-width-container govuk-main-wrapper">
  <div class="govuk-grid-row">
    <div class="govuk-grid-column-two-thirds">
      ${html}
    </div>
  </div>
</div>`
}

function renderPage(title, content) {
  const head = headPartial.replace('{{TITLE}}', title)

  return `<!DOCTYPE html>
<html lang="en" class="govuk-template">
  <head>
    ${head}
  </head>
  <body class="govuk-template__body">
    <script>document.body.className += ' js-enabled' + ('noModule' in HTMLScriptElement.prototype ? ' govuk-frontend-supported' : '');</script>
    ${headerPartial}
    <main id="main-content">
      ${content}
    </main>
    ${footerPartial}
    <script type="module">
      import { initAll } from '/assets/govuk-frontend.min.js'
      initAll()
    </script>
    <script type="module" src="/scripts/sign-in.js"></script>
  </body>
</html>
`
}

rmSync(dist, { recursive: true, force: true })
mkdirSync(dist, { recursive: true })

for (const page of pages) {
  if (!existsSync(page.contentPath)) {
    throw new Error(`Public site content not found: ${page.contentPath}`)
  }

  let content = readFileSync(page.contentPath, 'utf8')
  if (page.wrap) {
    content = wrapContent(content)
  }

  const html = renderPage(page.title, content)
  const outputFile = join(dist, page.outputPath)
  mkdirSync(dirname(outputFile), { recursive: true })
  writeFileSync(outputFile, html)
}

cpSync(join(publicSiteRoot, 'scripts'), join(dist, 'scripts'), {
  recursive: true,
})

const govukDist = join(frontendRoot, 'node_modules/govuk-frontend/dist/govuk')
const assetsDist = join(dist, 'assets')
mkdirSync(assetsDist, { recursive: true })
cpSync(join(govukDist, 'assets/images'), join(assetsDist, 'images'), {
  recursive: true,
})
cpSync(join(govukDist, 'assets/fonts'), join(assetsDist, 'fonts'), {
  recursive: true,
})
cpSync(
  join(govukDist, 'assets/manifest.json'),
  join(assetsDist, 'manifest.json')
)
cpSync(join(publicSiteRoot, 'assets/images'), join(assetsDist, 'images'), {
  recursive: true,
})
cpSync(
  join(govukDist, 'govuk-frontend.min.css'),
  join(assetsDist, 'govuk-frontend.min.css')
)
cpSync(
  join(govukDist, 'govuk-frontend.min.js'),
  join(assetsDist, 'govuk-frontend.min.js')
)
cpSync(
  join(frontendRoot, 'styles/public-page.css'),
  join(assetsDist, 'public-page.css')
)

cpSync(join(frontendRoot, 'public/logos'), join(dist, 'logos'), {
  recursive: true,
})

console.log(`Public site built to ${dist}`)
