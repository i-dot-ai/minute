/* eslint-env browser */

/**
 * @param {string} hostname
 * @returns {string}
 */
function getSignInHref (hostname) {
  if (hostname === 'localhost') return 'http://localhost:3000/'

  if (!hostname.endsWith('.i.ai.gov.uk')) {
    return 'https://minute.ai.cabinetoffice.gov.uk/'
  }

  const prefix = hostname.slice(0, -'.i.ai.gov.uk'.length)
  if (prefix === 'minute') {
    return 'https://minute.ai.cabinetoffice.gov.uk/'
  }
  if (prefix.startsWith('minute.')) {
    const env = prefix.slice('minute.'.length)
    return `https://minute-${env}.ai.cabinetoffice.gov.uk/`
  }

  return 'https://minute.ai.cabinetoffice.gov.uk/'
}

function initSignInLinks () {
  const signInButtons = document.querySelectorAll('.sign-in-button')
  if (!signInButtons.length) return

  signInButtons.forEach((link) => {
    link.href = getSignInHref(location.hostname)
  })
}

initSignInLinks()
