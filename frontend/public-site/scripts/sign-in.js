/* eslint-env browser */

/**
 * @param {string} hostname
 * @returns {string}
 */
export const getSignInHref = (hostname) => {
  if (hostname === 'localhost') return 'http://localhost:8081/'
  const PUBLIC_HOSTNAME_END = '.ai.gov.uk'
  const INTERNAL_HOSTNAME_END = '.i.ai.gov.uk'
  if (hostname.endsWith(PUBLIC_HOSTNAME_END)) {
    return `https://${hostname.replace(PUBLIC_HOSTNAME_END, INTERNAL_HOSTNAME_END)}/`
  }
  return 'https://minute.i.ai.gov.uk/'
}

const initSignInLinks = () => {
  /** @type {NodeListOf<HTMLAnchorElement>} */
  const signInButtons = document.querySelectorAll('.sign-in-button')
  if (!signInButtons.length) return

  signInButtons.forEach((link) => {
    link.href = getSignInHref(location.hostname)
  })
}

initSignInLinks()
