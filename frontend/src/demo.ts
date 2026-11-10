export type Step = 'welcome' | 'bank' | 'income' | 'expenses' | 'plan' | 'compare' | 'overview'
export type Cadence = 'once' | 'weekly' | 'biweekly' | 'monthly'

export interface ScheduledEntry {
  id: string
  name: string
  cents: number
  date: string
  cadence: Cadence
}

export interface Allocation {
  id: string
  name: string
  amount: string
}

export interface Demo {
  step: Step
  connected: boolean
  income: ScheduledEntry[]
  expenses: ScheduledEntry[]
  plan: Allocation[]
  accepted: Allocation[]
}

export const storageKey = 'agentic-finance-sample-v1'

export const cadences: Record<Cadence, string> = {
  once: 'One time',
  weekly: 'Weekly',
  biweekly: 'Every two weeks',
  monthly: 'Monthly',
}

export const sampleHistory = [
  {
    month: 'October 2026',
    income: 212000,
    saved: 9000,
    spending: { rent: 40000, utilities: 13800, gas: 12800, spend: 27200 },
  },
  {
    month: 'September 2026',
    income: 198000,
    saved: 7500,
    spending: { rent: 40000, utilities: 12600, gas: 8600, spend: 24900 },
  },
  {
    month: 'August 2026',
    income: 204000,
    saved: 11000,
    spending: { rent: 40000, utilities: 14900, gas: 9300, spend: 25600 },
  },
]

const trackedSpending: ReadonlyMap<string, keyof (typeof sampleHistory)[number]['spending']> =
  new Map([
    ['rent', 'rent'],
    ['utilities', 'utilities'],
    ['gas', 'gas'],
    ['spend', 'spend'],
  ])

export const sampleCash = 148260

export function freshDemo(): Demo {
  return {
    step: 'welcome',
    connected: false,
    income: [
      { id: 'job', name: 'Campus job', cents: 85000, date: '2026-11-13', cadence: 'biweekly' },
      { id: 'gig', name: 'Freelance project', cents: 26000, date: '2026-11-20', cadence: 'once' },
    ],
    expenses: [
      { id: 'rent-bill', name: 'Rent', cents: 40000, date: '2026-12-01', cadence: 'monthly' },
      { id: 'utility-bill', name: 'Utilities', cents: 14000, date: '2026-11-18', cadence: 'monthly' },
    ],
    plan: [
      { id: 'spend', name: 'Spend', amount: '300' },
      { id: 'save', name: 'Save', amount: '150' },
      { id: 'rent', name: 'Rent', amount: '400' },
      { id: 'utilities', name: 'Utilities', amount: '140' },
      { id: 'gas', name: 'Gas', amount: '80' },
    ],
    accepted: [],
  }
}

export function loadDemo(): Demo {
  try {
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      const demo: Demo = JSON.parse(saved)
      if (
        ['welcome', 'bank', 'income', 'expenses', 'plan', 'compare', 'overview'].includes(demo.step) &&
        typeof demo.connected === 'boolean' &&
        [demo.income, demo.expenses, demo.plan, demo.accepted].every(Array.isArray)
      ) {
        return demo
      }
    }
  } catch {
    // The flow remains usable when browser storage is unavailable.
  }
  return freshDemo()
}

const dollars = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const dates = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

export function money(cents: number) {
  return dollars.format(cents / 100)
}

export function dateLabel(date: string) {
  return dates.format(new Date(date))
}

export function toCents(value: string): number | null {
  if (!/^\d{1,7}(?:\.\d{1,2})?$/.test(value.trim())) return null
  return Math.round(Number(value) * 100)
}

export function totalPlan(plan: Allocation[]) {
  return plan.reduce((total, row) => total + (toCents(row.amount) ?? 0), 0)
}

const occurrencesPerYear: Record<Cadence, number> = {
  once: 0,
  weekly: 52,
  biweekly: 26,
  monthly: 12,
}

export function monthlyEstimate(entries: ScheduledEntry[]) {
  return Math.round(entries.reduce(
    (total, entry) => total + entry.cents * occurrencesPerYear[entry.cadence],
    0,
  ) / 12)
}

export function comparePlan(plan: Allocation[], connected: boolean) {
  return plan.map((row) => {
    const category = trackedSpending.get(row.id)
    const average = connected && category
      ? Math.round(sampleHistory.reduce((total, month) => total + month.spending[category], 0)
        / sampleHistory.length)
      : null
    const proposed = toCents(row.amount) ?? 0
    const suggested = average !== null && average > proposed ? Math.ceil(average / 500) * 500 : proposed
    return { row, average, proposed, suggested }
  })
}

export function latestActivity(id: string) {
  const latest = sampleHistory[0]
  const category = trackedSpending.get(id)
  if (category) return latest.spending[category]
  return id === 'save' ? latest.saved : null
}
