const API_BASE_URL = '/api'
const INTELLIGENCE_API_BASE_URL =
  import.meta.env.VITE_INTELLIGENCE_API_BASE_URL || '/intelligence-api'

async function readError(response) {
  try {
    const body = await response.json()

    if (typeof body === 'string') {
      return body
    }

    if (body.detail) {
      return body.detail
    }

    return JSON.stringify(body)
  } catch {
    return `Request failed with status ${response.status}`
  }
}

export async function checkServerHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error('Unable to connect to the backend')
  }

  return response.json()
}

export async function getMissionOverview() {
  const response = await fetch(
    `${INTELLIGENCE_API_BASE_URL}/mission/overview`,
  )

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function getMissionAlerts() {
  const response = await fetch(
    `${INTELLIGENCE_API_BASE_URL}/mission/alerts`,
  )

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function getAnalysis(astronautId, { readingId } = {}) {
  const query = readingId
    ? `?reading_id=${encodeURIComponent(readingId)}`
    : ''
  const response = await fetch(
    `${INTELLIGENCE_API_BASE_URL}/analysis/${encodeURIComponent(
      astronautId,
    )}${query}`,
  )

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function getReadings(astronautId, { limit = 5000 } = {}) {
  const response = await fetch(
    `${INTELLIGENCE_API_BASE_URL}/readings/${encodeURIComponent(
      astronautId,
    )}?limit=${limit}`,
  )

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function getAstronautDirectory() {
  const response = await fetch(`${API_BASE_URL}/astronauts`)

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  const body = await response.json()
  return Array.isArray(body) ? body : body.astronauts ?? []
}
