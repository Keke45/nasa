import { useEffect, useState } from 'react'
import { checkServerHealth } from './services/api'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    async function fetchHealth() {
      try {
        const data = await checkServerHealth()
        setHealth(data)
      } catch (err) {
        setError(err.message)
      }
    }

    fetchHealth()
  }, [])

  return (
    <main>
      <h1>Astronaut Health Intelligence</h1>

      <h2>System Status</h2>

      {health && (
        <div>
          <p>Backend: {health.status}</p>
          <p>Database: {health.database}</p>
        </div>
      )}

      {error && <p>{error}</p>}
    </main>
  )
}

export default App