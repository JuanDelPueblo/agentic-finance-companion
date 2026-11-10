import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'

import { App } from './App'
import { comparePlan, freshDemo, getPlanOverview, loadDemo, monthlyEstimate, storageKey, toCents } from './demo'

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

it('opens the accepted plan when restoring a demo saved before navigation was added', () => {
  const demo = freshDemo()
  demo.step = 'overview'
  demo.accepted = demo.plan.map((row) => row.id === 'gas' ? { ...row, amount: '105.00' } : row)
  delete demo.planDraft
  localStorage.setItem(storageKey, JSON.stringify(demo))

  expect(loadDemo().plan).toEqual(demo.accepted)
})

it('checks spending and savings targets without treating missing activity as on track', () => {
  const demo = freshDemo()
  demo.connected = true
  demo.accepted = [
    { id: 'rent', name: 'Rent', amount: '400' },
    { id: 'save', name: 'Save', amount: '90' },
  ]
  expect(getPlanOverview(demo).state).toBe('on-track')

  demo.accepted[0].amount = '399'
  expect(getPlanOverview(demo).state).toBe('attention')

  demo.accepted[0].amount = '400'
  demo.accepted[1].amount = '100'
  expect(getPlanOverview(demo).state).toBe('attention')

  demo.accepted[1].amount = '90'
  demo.accepted.push({ id: 'custom-books', name: 'Books', amount: '50' })
  expect(getPlanOverview(demo).state).toBe('pending')

  demo.connected = false
  expect(getPlanOverview(demo).state).toBe('pending')
})
