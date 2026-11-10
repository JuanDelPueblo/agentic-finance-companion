import { useEffect, useState, type RefObject } from 'react'

import { comparePlan, latestActivity, money, monthlyEstimate, sampleCash, sampleHistory, toCents, type Demo } from './demo'

interface ResultProps {
  demo: Demo
  heading: RefObject<HTMLHeadingElement | null>
  onEdit: () => void
}

interface ReviewProps extends ResultProps {
  onBack: () => void
  onAccept: () => void
}

export function PlanReview({ demo, heading, onBack, onEdit, onAccept }: ReviewProps) {
  const [comparing, setComparing] = useState(true)

  useEffect(() => {
    const timer = window.setTimeout(() => setComparing(false), 650)
    return () => window.clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (!comparing) heading.current?.focus()
  }, [comparing, heading])

  if (comparing) {
    return (
      <section className="screen loading" aria-busy="true">
        <div className="spinner" aria-hidden="true" />
        <h1 ref={heading} tabIndex={-1}>Comparing your plan</h1>
        <p role="status">{demo.connected ? 'Checking your allocations against sample spending history…' : 'Reviewing your monthly allocations…'}</p>
      </section>
    )
  }

  const rows = comparePlan(demo.plan, demo.connected)
  const total = rows.reduce((sum, row) => sum + row.suggested, 0)

  return (
    <section className="screen">
      <p className="eyebrow">Plan review</p>
      <h1 ref={heading} tabIndex={-1}>Suggested plan</h1>
      <p className="intro">
        {demo.connected
          ? 'Where sample spending averaged more than your draft, we rounded the average up to the next $5.'
          : 'No sample bank history is connected, so the suggested amounts match your draft.'}
      </p>
      <div className="metrics">
        <div><span>Monthly recurring income</span><strong>{money(monthlyEstimate(demo.income))}</strong></div>
        <div><span>Monthly recurring expenses</span><strong>{money(monthlyEstimate(demo.expenses))}</strong></div>
        <div><span>Suggested monthly total</span><strong>{money(total)}</strong></div>
      </div>
      <div className="comparison">
        <table>
          <thead><tr><th scope="col">Category</th><th scope="col">Draft</th><th scope="col">3-month avg.</th><th scope="col">Suggested</th></tr></thead>
          <tbody>
            {rows.map(({ row, proposed, average, suggested }) => (
              <tr key={row.id}>
                <th scope="row">{row.name}</th>
                <td>{money(proposed)}</td>
                <td>{average === null ? '—' : money(average)}</td>
                <td className={suggested > proposed ? 'adjusted' : ''}>{money(suggested)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="step-actions">
        <button className="button button-secondary" onClick={onBack}><span aria-hidden="true">←</span> Back</button>
        <div className="step-next">
          <button className="button button-secondary" onClick={onEdit}>Edit suggestion</button>
          <button className="button button-primary" onClick={onAccept}>Accept plan <span aria-hidden="true">→</span></button>
        </div>
      </div>
    </section>
  )
}

export function Overview({ demo, heading, onEdit }: ResultProps) {
  const [view, setView] = useState<'balances' | 'history'>('balances')

  return (
    <section className="screen">
      <p className="eyebrow">Plan accepted</p>
      <h1 ref={heading} tabIndex={-1}>Balances and History</h1>
      <p className="intro">See where you stand and revisit recent months.</p>
      <div className="view-switch" role="group" aria-label="Overview view">
        <button aria-pressed={view === 'balances'} onClick={() => setView('balances')}>Balances</button>
        <button aria-pressed={view === 'history'} onClick={() => setView('history')}>History</button>
      </div>
      {view === 'balances' ? (
        <>
          {demo.connected && (
            <div className="cash-summary"><span>Available sample cash</span><strong>{money(sampleCash)}</strong></div>
          )}
          <div className="list-heading">
            <h2>Budget progress</h2>
            <span className="fine-print">{demo.connected ? sampleHistory[0].month : 'Monthly plan'}</span>
          </div>
          <ul className="balance-list">
            {demo.accepted.map((row) => {
              const activity = demo.connected ? latestActivity(row.id) : null
              const goal = toCents(row.amount) ?? 0
              const overBudget = row.id !== 'save' && activity !== null && activity > goal
              const percent = activity === null ? 0 : goal ? Math.min(activity / goal, 1) * 100 : activity > 0 ? 100 : 0
              return (
                <li key={row.id}>
                  <div className="balance-row">
                    <strong>{row.name}</strong>
                    {overBudget && <span className="warning">Over budget</span>}
                    <span className="balance-amount">
                      {activity === null ? `Target ${money(goal)}` : `${money(activity)} / ${money(goal)}`}
                    </span>
                  </div>
                  {activity === null
                    ? <small>No sample activity</small>
                    : <div className={overBudget ? 'progress-track over-budget' : 'progress-track'} aria-hidden="true">
                        <span style={{ width: `${percent}%` }} />
                      </div>}
                </li>
              )
            })}
          </ul>
          <div className="step-actions end"><button className="button button-secondary" onClick={onEdit}>Edit plan</button></div>
        </>
      ) : (
        <>
          <h2 className="history-heading">Monthly history</h2>
          {demo.connected ? (
            <div className="history-list">
              {sampleHistory.map((month) => (
                <article key={month.month} className="history-card">
                  <h3>{month.month}</h3>
                  <dl>
                    <div><dt>Income</dt><dd>{money(month.income)}</dd></div>
                    <div><dt>Spending</dt><dd>{money(Object.values(month.spending).reduce((total, amount) => total + amount, 0))}</dd></div>
                    <div><dt>Saved</dt><dd>{money(month.saved)}</dd></div>
                  </dl>
                </article>
              ))}
            </div>
          ) : <p className="empty-state">No sample history. Reset the demo and connect the sample bank to explore past months.</p>}
          <div className="step-actions">
            <button className="button button-secondary" onClick={() => setView('balances')}><span aria-hidden="true">←</span> Back to balances</button>
          </div>
        </>
      )}
    </section>
  )
}
