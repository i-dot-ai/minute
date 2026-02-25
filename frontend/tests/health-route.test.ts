import { expect, test } from 'vitest'
import { GET } from '../app/health/route'

test('GET /health returns status ok', async () => {
  const response = await GET()
  const body = await response.json()

  expect(response.status).toBe(200)
  expect(body).toEqual({ status: 'ok' })
})
