import { useState } from 'react'
import './App.css'

type Incident = {
  incident_id: string
  title: string
  service: string
  environment: string
  severity: string
  error_message: string
  description: string
  traffic: number
  database: string
  status: string
}

type Memory = {
  content: string
  metadata?: Record<string, unknown>
  score?: number
}

type AgentResult = {
  summary?: string
  likely_root_cause?: string
  confidence?: string
  historical_evidence?: string[]
  recommended_actions?: string[]
  warnings?: string[]
  reasoning?: string
}

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [agent, setAgent] = useState<AgentResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [action, setAction] = useState('')
  const [result, setResult] = useState<'success' | 'failed'>('success')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [learned, setLearned] = useState(false)

  async function loadIncidents() {
    try {
      setError('')

      const response = await fetch(`${API_BASE}/api/incidents`)

      if (!response.ok) {
        throw new Error('Failed to load incidents')
      }

      const data = await response.json()
      setIncidents(data.incidents)

      if (data.incidents.length > 0) {
        setSelectedIncident(data.incidents[0])
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to backend',
      )
    }
  }

  async function investigate(incident: Incident) {
    try {
      setLoading(true)
      setError('')
      setLearned(false)

      const response = await fetch(
        `${API_BASE}/api/incidents/${incident.incident_id}/agent-investigate`,
        {
          method: 'POST',
        },
      )

      if (!response.ok) {
        throw new Error('Investigation failed')
      }

      const data = await response.json()

      setSelectedIncident(data.incident)
      setMemories(data.memories || [])
      setAgent(data.agent || null)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Investigation failed',
      )
    } finally {
      setLoading(false)
    }
  }

  async function recordAction() {
    if (!selectedIncident || !action.trim()) {
      setError('Enter an action before saving.')
      return
    }

    try {
      setSaving(true)
      setError('')

      const response = await fetch(
        `${API_BASE}/api/incidents/${selectedIncident.incident_id}/actions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action,
            result,
            reason,
          }),
        },
      )

      if (!response.ok) {
        throw new Error('Failed to record action')
      }

      setLearned(true)
      setAction('')
      setReason('')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to save action',
      )
    } finally {
      setSaving(false)
    }
  }

  function selectIncident(incident: Incident) {
    setSelectedIncident(incident)
    setMemories([])
    setAgent(null)
    setLearned(false)
    setError('')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-mark">IQ</span>
            <span>IncidentIQ</span>
          </div>

          <p className="brand-subtitle">
            Memory-powered AI incident response
          </p>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          AI INCIDENT AGENT ONLINE
        </div>
      </header>

      <main className="dashboard">
        <section className="hero-section">
          <div>
            <p className="eyebrow">PRODUCTION INCIDENT RESPONSE</p>

            <h1>
              Investigate incidents with engineering hindsight.
            </h1>

            <p className="hero-copy">
              IncidentIQ recalls what engineers tried before, what worked,
              what failed, and uses those experiences when investigating the
              next incident.
            </p>
          </div>

          <div className="hero-stat">
            <span>LEARNING LOOP</span>
            <strong>ACTIVE</strong>
            <small>Memory → Reasoning → Action → Learning</small>
          </div>
        </section>

        <div className="main-grid">
          <aside className="incident-sidebar panel">
            <div className="panel-heading">
              <div>
                <span className="section-label">INCIDENTS</span>
                <h2>Production queue</h2>
              </div>

              <button
                className="small-button"
                onClick={loadIncidents}
              >
                Refresh
              </button>
            </div>

            {incidents.length === 0 ? (
              <div className="empty-state">
                <p>No incidents loaded.</p>

                <button
                  className="primary-button"
                  onClick={loadIncidents}
                >
                  Load incidents
                </button>
              </div>
            ) : (
              <div className="incident-list">
                {incidents.map((incident) => (
                  <button
                    key={incident.incident_id}
                    className={`incident-card ${
                      selectedIncident?.incident_id ===
                      incident.incident_id
                        ? 'selected'
                        : ''
                    }`}
                    onClick={() => selectIncident(incident)}
                  >
                    <div className="incident-card-top">
                      <span>{incident.incident_id}</span>

                      <span
                        className={`severity ${incident.severity.toLowerCase()}`}
                      >
                        {incident.severity}
                      </span>
                    </div>

                    <strong>{incident.title}</strong>

                    <small>
                      {incident.service} · {incident.status}
                    </small>
                  </button>
                ))}
              </div>
            )}
          </aside>

          <section className="workspace">
            {!selectedIncident ? (
              <div className="panel empty-workspace">
                <h2>Select an incident</h2>

                <p>
                  Load the production incident queue to begin an
                  investigation.
                </p>
              </div>
            ) : (
              <>
                <section className="panel incident-overview">
                  <div className="overview-header">
                    <div>
                      <div className="incident-id">
                        {selectedIncident.incident_id}
                      </div>

                      <h2>{selectedIncident.title}</h2>

                      <p>{selectedIncident.description}</p>
                    </div>

                    <button
                      className="investigate-button"
                      onClick={() => investigate(selectedIncident)}
                      disabled={loading}
                    >
                      {loading
                        ? 'Investigating...'
                        : 'Run AI Investigation'}
                    </button>
                  </div>

                  <div className="signal-grid">
                    <div>
                      <span>SEVERITY</span>
                      <strong>{selectedIncident.severity}</strong>
                    </div>

                    <div>
                      <span>SERVICE</span>
                      <strong>{selectedIncident.service}</strong>
                    </div>

                    <div>
                      <span>ENVIRONMENT</span>
                      <strong>{selectedIncident.environment}</strong>
                    </div>

                    <div>
                      <span>TRAFFIC</span>
                      <strong>{selectedIncident.traffic}</strong>
                    </div>

                    <div>
                      <span>DATABASE</span>
                      <strong>{selectedIncident.database}</strong>
                    </div>

                    <div>
                      <span>ERROR</span>
                      <strong>{selectedIncident.error_message}</strong>
                    </div>
                  </div>
                </section>

                <section className="two-column">
                  <div className="panel">
                    <div className="panel-heading">
                      <div>
                        <span className="section-label">
                          AI INVESTIGATION
                        </span>

                        <h2>Diagnosis</h2>
                      </div>

                      {agent?.confidence && (
                        <span className="confidence">
                          {agent.confidence}
                        </span>
                      )}
                    </div>

                    {!agent ? (
                      <div className="placeholder">
                        <div className="placeholder-icon">AI</div>

                        <p>
                          Run the investigation to combine the current
                          incident with historical engineering experience.
                        </p>
                      </div>
                    ) : (
                      <div className="diagnosis">
                        <div className="diagnosis-block">
                          <span>LIKELY ROOT CAUSE</span>

                          <strong>
                            {agent.likely_root_cause ||
                              'Not determined'}
                          </strong>
                        </div>

                        <div className="diagnosis-block">
                          <span>SUMMARY</span>

                          <p>
                            {agent.summary ||
                              'No summary returned.'}
                          </p>
                        </div>

                        {agent.reasoning && (
                          <div className="diagnosis-block">
                            <span>REASONING</span>

                            <p>{agent.reasoning}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="panel">
                    <div className="panel-heading">
                      <div>
                        <span className="section-label">
                          HINDSIGHT
                        </span>

                        <h2>Historical experience</h2>
                      </div>

                      <span className="memory-count">
                        {memories.length} memories
                      </span>
                    </div>

                    {memories.length === 0 ? (
                      <div className="placeholder">
                        <div className="placeholder-icon">02</div>

                        <p>
                          Historical troubleshooting experience will
                          appear here after investigation.
                        </p>
                      </div>
                    ) : (
                      <>
                        {agent?.historical_evidence?.length ? (
                          <div className="hindsight-lessons">
                            <div className="section-label">
                              WHAT THE AI LEARNED
                            </div>

                            <ul>
                              {agent.historical_evidence.map(
                                (lesson, index) => (
                                  <li key={index}>{lesson}</li>
                                ),
                              )}
                            </ul>
                          </div>
                        ) : null}

                        <div className="memory-list">
                          {memories.map((memory, index) => {
                            const content = memory.content || ''
                            const metadata = memory.metadata || {}

                            const result = String(
                              metadata.result || '',
                            ).toLowerCase()

                            const success =
                              result === 'success' ||
                              content
                                .toLowerCase()
                                .includes('outcome: success')

                            const failed =
                              result === 'failed' ||
                              content
                                .toLowerCase()
                                .includes('outcome: failed')

                            return (
                              <div
                                className={`memory-item ${
                                  success
                                    ? 'memory-success'
                                    : failed
                                      ? 'memory-failed'
                                      : ''
                                }`}
                                key={`${content}-${index}`}
                              >
                                <div className="memory-icon">
                                  {success
                                    ? '✓'
                                    : failed
                                      ? '×'
                                      : '•'}
                                </div>

                                <div>
                                  <span>
                                    {success
                                      ? 'SUCCESSFUL EXPERIENCE'
                                      : failed
                                        ? 'FAILED EXPERIENCE'
                                        : 'HISTORICAL EXPERIENCE'}
                                  </span>

                                  <p>{content}</p>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </>
                    )}
                  </div>
                </section>

                <section className="two-column">
                  <div className="panel">
                    <div className="panel-heading">
                      <div>
                        <span className="section-label">
                          NEXT STEPS
                        </span>

                        <h2>AI recommendations</h2>
                      </div>
                    </div>

                    {!agent?.recommended_actions?.length ? (
                      <div className="placeholder">
                        <p>
                          Run an investigation to generate
                          recommendations.
                        </p>
                      </div>
                    ) : (
                      <>
                        <ol className="recommendation-list">
                          {agent.recommended_actions.map(
                            (item, index) => (
                              <li key={index}>{item}</li>
                            ),
                          )}
                        </ol>

                        <div className="recommendation-evidence">
                          <div className="recommendation-evidence-header">
                            <span className="section-label">
                              WHY THIS RECOMMENDATION?
                            </span>
                          </div>

                          <div className="evidence-chain">
                            <div className="evidence-step current">
                              <div className="evidence-marker">01</div>

                              <div>
                                <strong>Current incident evidence</strong>

                                <p>
                                  {selectedIncident.error_message} detected
                                  on {selectedIncident.service} with{' '}
                                  {selectedIncident.traffic} traffic.
                                </p>
                              </div>
                            </div>

                            {memories.length > 0 && (
                              <div className="evidence-step historical">
                                <div className="evidence-marker">02</div>

                                <div>
                                  <strong>Historical engineering evidence</strong>

                                  <p>
                                    IncidentIQ found relevant previous actions
                                    and their outcomes in incident memory.
                                  </p>

                                  <div className="evidence-memory-list">
                                    {memories.slice(0, 3).map((memory, index) => {
                                      const content = memory.content || ''
                                      const metadata = memory.metadata || {}

                                      const memoryResult = String(
                                        metadata.result || '',
                                      ).toLowerCase()

                                      const isSuccess =
                                        memoryResult === 'success' ||
                                        content
                                          .toLowerCase()
                                          .includes('outcome: success')

                                      const isFailed =
                                        memoryResult === 'failed' ||
                                        content
                                          .toLowerCase()
                                          .includes('outcome: failed')

                                      return (
                                        <div
                                          className={`evidence-memory ${
                                            isSuccess
                                              ? 'evidence-success'
                                              : isFailed
                                                ? 'evidence-failed'
                                                : ''
                                          }`}
                                          key={`${content}-${index}`}
                                        >
                                          <span className="evidence-result">
                                            {isSuccess
                                              ? '✓ SUCCESS'
                                              : isFailed
                                                ? '× FAILED'
                                                : '• EXPERIENCE'}
                                          </span>

                                          <span>{content}</span>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              </div>
                            )}

                            {agent.historical_evidence?.length ? (
                              <div className="evidence-step learned">
                                <div className="evidence-marker">03</div>

                                <div>
                                  <strong>AI learned from experience</strong>

                                  <ul className="learned-evidence-list">
                                    {agent.historical_evidence
                                      .slice(0, 3)
                                      .map((lesson, index) => (
                                        <li key={index}>{lesson}</li>
                                      ))}
                                  </ul>
                                </div>
                              </div>
                            ) : null}

                            <div className="evidence-conclusion">
                              <span>CONCLUSION</span>

                              <p>
                                The recommendation is based on the current
                                incident signals and previously recorded
                                engineering outcomes — not on the current
                                incident alone.
                              </p>
                            </div>
                          </div>
                        </div>
                      </>
                    )}

                    {!!agent?.warnings?.length && (
                      <div className="warnings">
                        <span>WARNINGS</span>

                        {agent.warnings.map(
                          (warning, index) => (
                            <div
                              className="warning"
                              key={index}
                            >
                              <span>!</span>

                              <p>{warning}</p>
                            </div>
                          ),
                        )}
                      </div>
                    )}
                  </div>

                  <div className="panel action-panel">
                    <div className="panel-heading">
                      <div>
                        <span className="section-label">
                          LEARNING LOOP
                        </span>

                        <h2>Record engineer action</h2>
                      </div>
                    </div>

                    <label>
                      Action

                      <input
                        value={action}
                        onChange={(event) =>
                          setAction(event.target.value)
                        }
                        placeholder="e.g. Increase connection pool to 120"
                      />
                    </label>

                    <label>
                      Result

                      <select
                        value={result}
                        onChange={(event) =>
                          setResult(
                            event.target.value as
                              | 'success'
                              | 'failed',
                          )
                        }
                      >
                        <option value="success">
                          Success
                        </option>

                        <option value="failed">
                          Failed
                        </option>
                      </select>
                    </label>

                    <label>
                      Reason

                      <textarea
                        value={reason}
                        onChange={(event) =>
                          setReason(event.target.value)
                        }
                        placeholder="What happened after the action?"
                        rows={3}
                      />
                    </label>

                    <button
                      className="primary-button full-width"
                      onClick={recordAction}
                      disabled={saving}
                    >
                      {saving
                        ? 'Saving...'
                        : 'Save to Incident Memory'}
                    </button>

                    {learned && (
                      <div className="learned-message">
                        ✓ Experience recorded. Run the investigation
                        again to see the updated memory.
                      </div>
                    )}
                  </div>
                </section>
              </>
            )}
          </section>
        </div>

        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}
      </main>
    </div>
  )
}

export default App