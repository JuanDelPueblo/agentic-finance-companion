import { useEffect, useRef, useState, type ReactNode } from 'react'

import { api, type Schemas } from './api/client'
import { ScheduleEditor } from './ScheduleEditor'
import { Overview, PlanReview } from './PlanResults'
import {
  comparePlan, freshDemo, loadDemo, money, sampleCash, storageKey, toCents, totalPlan,
  type Allocation, type Step,
} from './demo'
import './app.css'

function BackendStatus() {
  const [health, setHealth] = useState<Schemas['Health']>()
  const [error, setError] = useState<string>()

  useEffect(() => {
    api
      .GET('/api/health')
      .then(({ data }) => (data ? setHealth(data) : setError('The backend returned an error.')))
      .catch(() => setError('Cannot reach the backend. Check that it is running.'))
  }, [])

  if (error) return <p>{error}</p>
  if (!health) return <p>Checking the backend…</p>
  return (
    <p>
      Backend: {health.status}. Database:{' '}
      {health.database.connected ? 'connected' : 'not connected'}.
    </p>
  )
}

function StepActions({ onBack, children }: { onBack?: () => void; children: ReactNode }) {
  return (
    <div className={onBack ? 'step-actions' : 'step-actions end'}>
      {onBack && (
        <button type="button" className="button button-secondary" onClick={onBack}>
          <span aria-hidden="true">←</span> Back
        </button>
      )}
      <div className="step-next">{children}</div>
    </div>
  )
}

export function App() {
  const [demo, setDemo] = useState(loadDemo)
  const [account, setAccount] = useState<'Login' | 'Signup' | null>(null)
  const [planError, setPlanError] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  const setupComplete = demo.accepted.length > 0
  const currentPage = demo.step === 'overview' ? 'Home' : demo.step === 'history' ? 'History' : 'Plan'

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(demo))
    } catch {
      // Users can still finish the demo in this tab.
    }
  }, [demo])

  useEffect(() => {
    heading.current?.focus()
  }, [demo.step, account])

  function go(step: Step) {
    setAccount(null)
    setPlanError('')
    setDemo((current) => ({ ...current, step }))
  }

  function changePlan(plan: Allocation[]) {
    setPlanError('')
    setDemo((current) => ({ ...current, plan, planDraft: true }))
  }

  function submitPlan(save: boolean) {
    if (!demo.plan.length || demo.plan.some((row) => !row.name.trim() || toCents(row.amount) === null)) {
      setPlanError('Add at least one category. Give each category a name and a valid dollar amount.')
      return
    }
    if (save) {
      const plan = demo.plan.map((row) => ({
        ...row,
        name: row.name.trim(),
        amount: row.amount.trim(),
      }))
      setPlanError('')
      setDemo((current) => ({
        ...current,
        step: 'overview',
        plan,
        accepted: plan,
        planDraft: false,
      }))
      return
    }
    go('compare')
  }

  function applySuggestion(step: 'plan' | 'overview') {
    const suggestion = comparePlan(demo.plan, demo.connected).map(({ row, suggested }) => ({
      ...row,
      name: row.name.trim(),
      amount: (suggested / 100).toFixed(2),
    }))
    setDemo((current) => ({
      ...current,
      step,
      plan: suggestion,
      planDraft: step === 'plan',
      ...(step === 'overview' ? { accepted: suggestion } : {}),
    }))
  }

  const title = (text: string) => <h1 ref={heading} tabIndex={-1}>{text}</h1>

  return (
    <>
      <main className={demo.step === 'welcome' && !account ? 'main welcome-main' : 'main'}>
        {setupComplete && (
          <nav className="app-nav" aria-label="Main navigation">
            <button aria-current={currentPage === 'Home' ? 'page' : undefined} onClick={() => go('overview')}>
              <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10Z" />
              </svg>
              <span>Home</span>
            </button>
            <button aria-current={currentPage === 'History' ? 'page' : undefined} onClick={() => go('history')}>
              <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 11a9 9 0 1 1 2.6 7.4M3 5v6h6m3-4v5l3 2" />
              </svg>
              <span>History</span>
            </button>
            <button aria-current={currentPage === 'Plan' ? 'page' : undefined} onClick={() => go('plan')}>
              <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true">
                <rect x="5" y="3" width="14" height="18" rx="2" />
                <path d="m8 9 1 1 2-2m2 1h3m-8 6 1 1 2-2m2 1h3" />
              </svg>
              <span>Plan</span>
            </button>
          </nav>
        )}
        {demo.step === 'welcome' && !account && (
          <section className="welcome">
            <div className="welcome-content">
              <h1 ref={heading} tabIndex={-1}>
                <span className="welcome-lead">Welcome to</span>{' '}Agentic Finances Companion
              </h1>
              <p className="intro">See what’s coming in, plan for what’s going out, and build a monthly plan around the way you get paid.</p>
              <div className="welcome-actions">
                <button className="button button-primary" onClick={() => go('bank')}>Demo <span aria-hidden="true">→</span></button>
                <button className="button button-secondary" onClick={() => setAccount('Login')}>Login</button>
                <button className="button button-secondary" onClick={() => setAccount('Signup')}>Signup</button>
              </div>
              <p className="fine-print">Explore with sample finances. No bank credentials needed.</p>
            </div>
            <div className="welcome-preview" aria-hidden="true">
              <svg className="dashboard-icon" viewBox="0 0 64 64" fill="none">
                <rect x="7" y="7" width="21" height="30" rx="4" />
                <rect x="36" y="7" width="21" height="16" rx="4" />
                <rect x="7" y="45" width="21" height="12" rx="4" />
                <rect x="36" y="31" width="21" height="26" rx="4" />
              </svg>
            </div>
          </section>
        )}
        {demo.step === 'welcome' && account && (
          <section className="screen">
            {title(account)}
            <p className="intro">
              {account === 'Login'
                ? 'Try signing in as the sample user.'
                : 'Explore the setup flow with a sample profile.'} The demo uses fictional account data.
            </p>
            <StepActions onBack={() => setAccount(null)}>
              <button className="button button-primary" onClick={() => go('bank')}>
                {account === 'Login' ? 'Continue as demo user' : 'Continue with sample profile'}
              </button>
            </StepActions>
          </section>
        )}
        {demo.step === 'bank' && (
          <section className="screen">
            {title('Connect bank account')}
            <p className="intro">Link a sample account to see how balances and recent spending can inform your plan.</p>
            <div className="bank-card">
              <div className="bank-icon">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="m3 9 9-5 9 5H3Zm2 11h14M7 10v7m5-7v7m5-7v7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <h2>Sample checking</h2>
                <p>{demo.connected ? 'Available cash' : 'Fictional balance and three months of history'}</p>
              </div>
              {demo.connected
                ? <strong className="bank-amount">{money(sampleCash)}</strong>
                : <button className="button button-secondary" onClick={() => setDemo((current) => ({ ...current, connected: true }))}>Connect sample bank</button>}
            </div>
            {demo.connected && <p className="fine-print" role="status">Sample bank connected.</p>}
            <StepActions onBack={() => go('welcome')}>
              {demo.connected
                ? <button className="button button-primary" onClick={() => go('income')}>Continue <span aria-hidden="true">→</span></button>
                : <button className="text-button" onClick={() => go('income')}>Skip for now</button>}
            </StepActions>
          </section>
        )}
        {(demo.step === 'income' || demo.step === 'expenses') && (
          <section className="screen" key={demo.step}>
            {title(demo.step === 'income' ? 'Income Sources' : 'Recurring Expenses')}
            <p className="intro">
              {demo.step === 'income'
                ? 'When do you expect to get paid? Include regular pay and one-time work.'
                : 'List the bills you expect to pay again so you can plan for them ahead of time.'}
            </p>
            {demo.step === 'income' ? (
              <ScheduleEditor kind="income" entries={demo.income} onChange={(income) => setDemo((current) => ({ ...current, income }))} />
            ) : (
              <ScheduleEditor kind="expense" entries={demo.expenses} onChange={(expenses) => setDemo((current) => ({ ...current, expenses }))} />
            )}
            <StepActions onBack={() => go(demo.step === 'income' ? 'bank' : 'income')}>
              <button className="button button-primary" onClick={() => go(demo.step === 'income' ? 'expenses' : 'plan')}>Continue <span aria-hidden="true">→</span></button>
            </StepActions>
          </section>
        )}
        {demo.step === 'plan' && (
          <section className="screen">
            {title('Financial plan')}
            <p className="intro">
              {setupComplete
                ? 'Update your allocations, then save your plan to update Home. You can also compare it with your spending history.'
                : 'Choose how much you want to set aside for each category.'}
            </p>
            <form onSubmit={(event) => {
              event.preventDefault()
              submitPlan(setupComplete)
            }}>
              <div className="allocation-list">
                {demo.plan.map((row) => (
                  <div className="allocation" key={row.id}>
                    {row.id.startsWith('custom-') ? (
                      <input
                        aria-label="Category name"
                        placeholder="Category name"
                        maxLength={40}
                        value={row.name}
                        onChange={(event) => changePlan(demo.plan.map((item) => item.id === row.id ? { ...item, name: event.target.value } : item))}
                      />
                    ) : <strong>{row.name}</strong>}
                    <label className="currency-input">
                      <span aria-hidden="true">$</span>
                      <input
                        aria-label={`${row.name || 'New category'} amount`}
                        inputMode="decimal"
                        placeholder="0.00"
                        value={row.amount}
                        onChange={(event) => changePlan(demo.plan.map((item) => item.id === row.id ? { ...item, amount: event.target.value } : item))}
                      />
                    </label>
                    <button
                      type="button"
                      className="text-button text-muted"
                      aria-label={`Remove ${row.name || 'new category'}`}
                      onClick={() => changePlan(demo.plan.filter((item) => item.id !== row.id))}
                    >Remove</button>
                  </div>
                ))}
              </div>
              <div className="list-heading plan-total">
                <button type="button" className="button button-small button-secondary" onClick={() => changePlan([...demo.plan, {
                  id: `custom-${crypto.randomUUID()}`, name: '', amount: '',
                }])}>+ Add category</button>
                <div><span>Monthly total</span><strong>{money(totalPlan(demo.plan))}</strong></div>
              </div>
              {planError && <p className="form-error" role="alert">{planError}</p>}
              <StepActions onBack={setupComplete ? undefined : () => go('expenses')}>
                {setupComplete && (
                  <button type="button" className="button button-secondary" onClick={() => submitPlan(false)}>Compare plan</button>
                )}
                <button className="button button-primary">
                  {setupComplete ? 'Save plan' : 'Compare plan'} <span aria-hidden="true">→</span>
                </button>
              </StepActions>
            </form>
          </section>
        )}
        {demo.step === 'compare' && (
          <PlanReview
            demo={demo}
            heading={heading}
            onBack={() => go('plan')}
            onEdit={() => applySuggestion('plan')}
            onAccept={() => applySuggestion('overview')}
          />
        )}
        {(demo.step === 'overview' || demo.step === 'history') && (
          <Overview
            demo={demo}
            heading={heading}
            view={demo.step === 'history' ? 'history' : 'balances'}
            onEdit={() => go('plan')}
          />
        )}
      </main>
      <footer className={setupComplete ? 'site-footer has-bottom-nav' : 'site-footer'}>
        <BackendStatus />
        {demo.step !== 'welcome' && (
          <button className="text-button text-muted" onClick={() => {
            setPlanError('')
            setDemo(freshDemo())
          }}>Reset demo</button>
        )}
      </footer>
    </>
  )
}
