import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'

import { ScheduleEditor } from './ScheduleEditor'
import { Overview, PlanReview } from './PlanResults'
import {
  comparePlan, freshDemo, loadDemo, money, sampleCash, storageKey, toCents, totalPlan,
  type Allocation, type Step,
} from './demo'
import './app.css'

const stages = [
  { id: 'bank', label: 'Bank account' },
  { id: 'income', label: 'Income' },
  { id: 'expenses', label: 'Expenses' },
  { id: 'plan', label: 'Plan' },
  { id: 'compare', label: 'Review' },
] as const

function Mark() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M5 17V7m0 8 5-5 4 3 5-6m-5 0h5v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function StepActions({ onBack, children }: { onBack: () => void; children: ReactNode }) {
  return (
    <div className="step-actions">
      <button type="button" className="button button-secondary" onClick={onBack}>
        <span aria-hidden="true">←</span> Back
      </button>
      <div className="step-next">{children}</div>
    </div>
  )
}

export function App() {
  const [demo, setDemo] = useState(loadDemo)
  const [account, setAccount] = useState<'Login' | 'Signup' | null>(null)
  const [planError, setPlanError] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  const activeStage = stages.findIndex(({ id }) => id === demo.step)

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
    setDemo((current) => ({ ...current, plan }))
  }

  function startComparison(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!demo.plan.length || demo.plan.some((row) => !row.name.trim() || toCents(row.amount) === null)) {
      setPlanError('Add at least one category. Give each category a name and a valid dollar amount.')
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
      ...(step === 'plan' ? { plan: suggestion } : { accepted: suggestion }),
    }))
  }

  const title = (text: string) => <h1 ref={heading} tabIndex={-1}>{text}</h1>

  return (
    <>
      <header className="site-header">
        <div className="site-header-inner">
          <div className="wordmark"><span className="brand-mark"><Mark /></span> Agentic Finances</div>
          <div className="header-actions">
            <span className="sample-badge"><span aria-hidden="true" /> Sample mode</span>
            {demo.step !== 'welcome' && (
              <button className="text-button text-muted" onClick={() => {
                setPlanError('')
                setDemo(freshDemo())
              }}>Reset demo</button>
            )}
          </div>
        </div>
      </header>
      <main className={demo.step === 'welcome' && !account ? 'main welcome-main' : 'main'}>
        {demo.step === 'welcome' && !account && (
          <section className="welcome">
            <div className="welcome-content">
              <p className="eyebrow">Personal finance companion</p>
              {title('Welcome to Agentic Finances Companion')}
              <p className="intro">See what’s coming in, plan for what’s going out, and build a monthly plan around the way you get paid.</p>
              <div className="welcome-actions">
                <button className="button button-primary" onClick={() => go('bank')}>Demo <span aria-hidden="true">→</span></button>
                <button className="button button-secondary" onClick={() => setAccount('Login')}>Login</button>
                <button className="button button-secondary" onClick={() => setAccount('Signup')}>Signup</button>
              </div>
              <p className="fine-print">Explore with sample finances. No bank credentials needed.</p>
            </div>
            <div className="welcome-preview" aria-hidden="true">
              <span className="preview-mark"><Mark /></span>
              <div className="preview-card">
                <span className="preview-label">Monthly plan</span>
                <strong>A place for every dollar</strong>
                <div className="preview-row"><span>Rent</span><b>$400.00</b></div>
                <div className="preview-track"><span style={{ width: '100%' }} /></div>
                <div className="preview-row"><span>Utilities</span><b>$138.00</b></div>
                <div className="preview-track"><span style={{ width: '78%' }} /></div>
                <div className="preview-row"><span>Savings</span><b>$90.00</b></div>
                <div className="preview-track"><span style={{ width: '60%' }} /></div>
              </div>
              <span className="preview-caption">Sample monthly snapshot</span>
            </div>
          </section>
        )}
        {demo.step === 'welcome' && account && (
          <section className="screen">
            <p className="eyebrow">Sample mode</p>
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
        {activeStage >= 0 && (
          <nav className="progress-nav" aria-label="Setup progress">
            <ol>
              {stages.map(({ id, label }, index) => (
                <li key={id} aria-current={index === activeStage ? 'step' : undefined}
                  className={index < activeStage ? 'complete' : ''}>
                  <span className="step-marker">{index + 1}</span><span className="stage-label">{label}</span>
                </li>
              ))}
            </ol>
            <span className="mobile-progress">Step {activeStage + 1} of {stages.length} · {stages[activeStage].label}</span>
          </nav>
        )}
        {demo.step === 'bank' && (
          <section className="screen">
            <p className="eyebrow">Bank account</p>
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
            <p className="eyebrow">{demo.step === 'income' ? 'Money coming in' : 'Money going out'}</p>
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
            <p className="eyebrow">Monthly allocations</p>
            {title('Financial plan')}
            <p className="intro">Choose how much you want to set aside for each category.</p>
            <form onSubmit={startComparison}>
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
              <StepActions onBack={() => go(demo.accepted.length ? 'overview' : 'expenses')}>
                <button className="button button-primary">Compare plan <span aria-hidden="true">→</span></button>
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
        {demo.step === 'overview' && (
          <Overview demo={demo} heading={heading} onEdit={() => {
            changePlan(demo.accepted)
            go('plan')
          }} />
        )}
      </main>
      <footer className="site-footer">Agentic Finances Companion <span>·</span> Interactive prototype</footer>
    </>
  )
}
