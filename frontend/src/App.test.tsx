import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { App } from './App'

afterEach(() => vi.unstubAllGlobals())

it('shows the backend status', async () => {
  const health = {
    status: 'ok',
    database: { connected: true },
  }
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(health)))

  render(<App />)

  expect(await screen.findByText(/Backend: ok/)).toHaveTextContent('Database: connected')
})
