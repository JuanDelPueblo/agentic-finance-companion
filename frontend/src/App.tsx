import { useEffect, useState } from 'react'

import { api, type Schemas } from './api/client'

// Placeholder page: shows that the frontend reaches the backend and the database.
export function App() {
  const [health, setHealth] = useState<Schemas['Health']>()
  const [error, setError] = useState<string>()

  useEffect(() => {
    api
      .GET('/api/health')
      .then(({ data }) => (data ? setHealth(data) : setError('The backend returned an error.')))
      .catch(() => setError('Cannot reach the backend. Check that it is running.'))
  }, [])

  return (
    <main>
      <h1>Agentic Finance Companion</h1>
      {error && <p role="alert">{error}</p>}
      {!health && !error && <p>Checking the backend…</p>}
      {health && (
        <p>
          Backend: {health.status}. Database:{' '}
          {health.database.connected ? 'connected' : 'not connected'}.
        </p>
      )}
    </main>
  )
}
