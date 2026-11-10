import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'

import { App } from './App'
import { comparePlan, freshDemo, monthlyEstimate, toCents } from './demo'

beforeEach(() => localStorage.clear())

it('opens the sample bank setup from the welcome screen', async () => {
  const user = userEvent.setup()
  render(<App />)

  expect(screen.getByRole('heading', { name: 'Welcome to Agentic Finances Companion' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Demo' }))
  expect(screen.getByRole('heading', { name: 'Connect bank account' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Connect sample bank' }))
  expect(screen.getByRole('status')).toHaveTextContent('Sample bank connected.')
})

it('suggests an increase when sample spending exceeds the draft', () => {
  const { plan, income } = freshDemo()
  const gas = comparePlan(plan, true).find(({ row }) => row.id === 'gas')
  expect(gas).toMatchObject({ proposed: 8000, average: 10233, suggested: 10500 })
  expect(comparePlan(plan, false).every(({ average, proposed, suggested }) =>
    average === null && proposed === suggested,
  )).toBe(true)
  expect(monthlyEstimate(income)).toBe(184167)
})

it('parses dollar input in cents and rejects excess decimal places', () => {
  expect(toCents('3.05')).toBe(305)
  expect(toCents('3.005')).toBeNull()
  expect(toCents('-3')).toBeNull()
})
