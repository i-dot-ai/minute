import DOMPurify from 'dompurify'

export const sanitizeTemplateHtml = (html: string) =>
  DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p',
      'br',
      'strong',
      'em',
      's',
      'code',
      'h1',
      'h2',
      'h3',
      'h4',
      'ul',
      'ol',
      'li',
    ],
    ALLOWED_ATTR: [],
  })
