import { useState, type FormEvent } from 'react'

import { cadences, dateLabel, money, toCents, type Cadence, type ScheduledEntry } from './demo'

interface Props {
  kind: 'income' | 'expense'
  entries: ScheduledEntry[]
  onChange: (entries: ScheduledEntry[]) => void
}

export function ScheduleEditor({ kind, entries, onChange }: Props) {
  const isIncome = kind === 'income'
  const nameLabel = isIncome ? 'Source name' : 'Expense name'
  const [editor, setEditor] = useState<ScheduledEntry | 'new' | null>(null)
  const [error, setError] = useState('')
  const editing = editor === 'new' ? null : editor

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const name = String(fields.get('name')).trim()
    const cents = toCents(String(fields.get('amount')))
    if (!name || cents === null || cents <= 0) {
      setError('Enter a name and a positive dollar amount with up to two decimal places.')
      return
    }

    const entry = {
      id: editing?.id ?? crypto.randomUUID(),
      name,
      cents,
      date: String(fields.get('date')),
      cadence: fields.get('cadence') as Cadence,
    }
    onChange(editing ? entries.map((item) => item.id === entry.id ? entry : item) : [...entries, entry])
    setEditor(null)
    setError('')
  }

  function open(entry: ScheduledEntry | 'new') {
    setEditor(entry)
    setError('')
  }

  return (
    <>
      <div className="list-heading">
        <h2>{isIncome ? 'Expected payments' : 'Recurring bills'}</h2>
        {!editor && (
          <button className="button button-small button-secondary" onClick={() => open('new')}>
            <span aria-hidden="true">+</span> {isIncome ? 'Add income' : 'Add expense'}
          </button>
        )}
      </div>
      {entries.length ? (
        <ul className="entry-list">
          {entries.map((entry) => (
            <li key={entry.id} className="entry">
              <div className="entry-description">
                <strong>{entry.name}</strong>
                <small>{cadences[entry.cadence]} · {dateLabel(entry.date)}</small>
              </div>
              <strong className="entry-amount">{money(entry.cents)}</strong>
              <div className="entry-actions">
                <button className="text-button" aria-label={`Edit ${entry.name}`} onClick={() => open(entry)}>Edit</button>
                <button
                  className="text-button text-muted"
                  aria-label={`Remove ${entry.name}`}
                  onClick={() => {
                    onChange(entries.filter((item) => item.id !== entry.id))
                    if (editing?.id === entry.id) setEditor(null)
                  }}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : <p className="empty-state">{isIncome ? 'No expected payments yet.' : 'No recurring bills yet.'}</p>}
      {editor && (
        <form className="editor" key={editing?.id ?? 'new'} onSubmit={save}>
          <h3>{editing ? 'Edit' : 'Add'} {kind}</h3>
          <div className="form-grid">
            <label>
              {nameLabel}
              <input name="name" defaultValue={editing?.name} required maxLength={60} />
            </label>
            <label>
              Amount (USD)
              <input
                name="amount"
                inputMode="decimal"
                placeholder="0.00"
                defaultValue={editing ? (editing.cents / 100).toFixed(2) : ''}
                required
              />
            </label>
            <label>
              {isIncome ? 'Next pay date' : 'Next due date'}
              <input type="date" name="date" defaultValue={editing?.date} required />
            </label>
            <label>
              Frequency
              <select name="cadence" defaultValue={editing?.cadence ?? 'monthly'}>
                {Object.entries(cadences).filter(([value]) => isIncome || value !== 'once').map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="editor-actions">
            <button type="button" className="button button-small button-secondary" onClick={() => setEditor(null)}>Cancel</button>
            <button className="button button-small button-primary">Save {kind}</button>
          </div>
        </form>
      )}
    </>
  )
}
