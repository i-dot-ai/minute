// Bridges a recording's known duration to the status page. The estimate there
// needs an audio duration, but right after recording neither the transcript nor
// a playable audio URL exists yet, so it would otherwise show no estimate while
// transcribing. We measure the blob once at submit time and stash it keyed by
// the new transcription id for the status page to read back.

const STORAGE_PREFIX = 'recording-duration-sec:'

/**
 * Decodes a media blob just far enough to read its duration in seconds.
 *
 * Blobs produced live by MediaRecorder (both recorders here) carry no duration
 * in their WebM header, so the element first reports `Infinity`. Seeking past
 * the end forces the browser to scan for the real end, which it then reports via
 * `durationchange` — the standard workaround for that container bug.
 */
export const measureAudioDurationSec = (blob: Blob): Promise<number | null> =>
  new Promise((resolve) => {
    if (typeof window === 'undefined') {
      resolve(null)
      return
    }
    const url = URL.createObjectURL(blob)
    const audio = document.createElement('audio')
    let settled = false

    const finish = (duration: number | null) => {
      if (settled) return
      settled = true
      URL.revokeObjectURL(url)
      resolve(duration !== null && Number.isFinite(duration) ? duration : null)
    }

    audio.preload = 'metadata'
    audio.onloadedmetadata = () => {
      if (Number.isFinite(audio.duration)) {
        finish(audio.duration)
        return
      }
      // Unknown/Infinity duration: seek far past the end to force a recalc.
      audio.ontimeupdate = () => {
        audio.ontimeupdate = null
        // Reset so the element is left in a clean state; duration is now known.
        audio.currentTime = 0
        finish(audio.duration)
      }
      audio.currentTime = Number.MAX_SAFE_INTEGER
    }
    audio.ondurationchange = () => {
      if (Number.isFinite(audio.duration)) finish(audio.duration)
    }
    audio.onerror = () => finish(null)
    audio.src = url
  })

export const storeRecordingDurationSec = (
  transcriptionId: string,
  durationSec: number | null
) => {
  if (typeof window === 'undefined' || durationSec === null) return
  try {
    sessionStorage.setItem(
      `${STORAGE_PREFIX}${transcriptionId}`,
      String(durationSec)
    )
  } catch {
    // sessionStorage can be unavailable (private mode/quota); the estimate just
    // stays hidden until the transcript or audio URL provides a duration.
  }
}

export const readRecordingDurationSec = (
  transcriptionId: string
): number | null => {
  if (typeof window === 'undefined') return null
  try {
    const value = sessionStorage.getItem(`${STORAGE_PREFIX}${transcriptionId}`)
    if (value === null) return null
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  } catch {
    return null
  }
}
