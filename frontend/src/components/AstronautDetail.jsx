import { useEffect, useMemo, useState } from 'react'
import { getAnalysis, getReadings } from '../services/api'
import MetricTrendChart from './MetricTrendChart'
import {
  CHART_METRICS,
  formatDate,
  formatMetric,
  formatNumber,
  formatRelativeTime,
  METRIC_META,
  SEVERITY_LABEL,
  severityRank,
  statusClass,
} from '../lib/format'

const RANGES = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
  { value: 'all', label: 'All' },
]

function formatDifference(value, unit) {
  if (value === null || value === undefined) {
    return '—'
  }

  if (Math.abs(value) < 0.005) {
    return 'At baseline'
  }

  const sign = value > 0 ? '+' : ''
  return `${sign}${formatMetric(value, unit)}`
}

function observationFor(item) {
  if (item.reason) {
    return item.reason
  }

  const label = item.metric_label || item.metric
  const difference = item.difference
  const direction = item.direction

  if (
    difference !== null &&
    difference !== undefined &&
    (direction === 'ABOVE' || direction === 'BELOW')
  ) {
    const amount = Math.abs(difference).toFixed(1)
    const measure = item.unit ? `${amount} ${item.unit}` : amount
    return `${label} is ${measure} ${direction.toLowerCase()} the personal baseline.`
  }

  return `${label} deviates from the personal baseline.`
}

function contributingFactors(item, flagged, trends) {
  const factors = []

  flagged.forEach((other) => {
    if (other.metric === item.metric) {
      return
    }
    const direction = String(other.direction || '').toLowerCase()
    factors.push(
      `${other.metric_label} ${direction} baseline`.trim(),
    )
  })

  Object.values(trends || {}).forEach((trend) => {
    if (!trend.direction || trend.direction === 'STABLE') {
      return
    }
    factors.push(
      `${trend.metric_label} trending ${trend.direction.toLowerCase()}`,
    )
  })

  return [...new Set(factors)].slice(0, 4)
}

function SummaryCard({ label, value, note }) {
  return (
    <article className="summary-card">
      <span className="summary-label">{label}</span>
      <strong>{value}</strong>
      <span className="summary-note">{note}</span>
    </article>
  )
}

export default function AstronautDetail({
  astronautId,
  directoryEntry,
  overviewEntry,
  refreshKey,
  onBack,
  onViewAlerts,
}) {
  const [analysis, setAnalysis] = useState(null)
  const [readings, setReadings] = useState([])
  const [loading, setLoading] = useState(true)
  const [readingsLoading, setReadingsLoading] = useState(true)
  const [error, setError] = useState('')
  const [readingsError, setReadingsError] = useState('')
  const [chartMetric, setChartMetric] = useState('heart_rate')
  const [rangeDays, setRangeDays] = useState(7)

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setReadingsLoading(true)
      setError('')
      setReadingsError('')

      const [analysisResult, readingsResult] =
        await Promise.allSettled([
          getAnalysis(astronautId),
          getReadings(astronautId),
        ])

      if (!active) {
        return
      }

      if (analysisResult.status === 'fulfilled') {
        setAnalysis(analysisResult.value)
      } else {
        setAnalysis(null)
        setError(analysisResult.reason.message)
      }

      if (readingsResult.status === 'fulfilled') {
        setReadings(readingsResult.value.readings ?? [])
      } else {
        setReadings([])
        setReadingsError(readingsResult.reason.message)
      }

      setLoading(false)
      setReadingsLoading(false)
    }

    load()

    return () => {
      active = false
    }
  }, [astronautId, refreshKey])

  const summary = analysis?.summary
  const baseline = analysis?.baseline
  const ml = analysis?.ml_anomaly
  const latest = analysis?.reading ?? overviewEntry?.latest_reading

  const anomalies = useMemo(() => {
    if (!analysis) {
      return []
    }

    return [...analysis.anomalies].sort(
      (left, right) =>
        severityRank(left.severity) -
        severityRank(right.severity),
    )
  }, [analysis])

  const flagged = useMemo(
    () =>
      anomalies.filter(
        (item) =>
          item.evaluated &&
          item.severity !== 'NORMAL' &&
          item.severity !== 'NOT_EVALUATED',
      ),
    [anomalies],
  )

  const anomalyByMetric = useMemo(() => {
    const map = {}
    anomalies.forEach((item) => {
      map[item.metric] = item
    })
    return map
  }, [anomalies])

  const severity =
    summary?.anomaly?.highest_severity ??
    overviewEntry?.severity ??
    'NOT_EVALUATED'
  const requiresReview =
    summary?.requires_review ??
    overviewEntry?.requires_review ??
    false

  const name = directoryEntry?.full_name || astronautId
  const mission = [
    directoryEntry?.mission_role,
    directoryEntry?.mission_name,
  ]
    .filter(Boolean)
    .join(' · ')

  const chartBaseline =
    anomalyByMetric[chartMetric]?.baseline_value ?? null
  const recommendations = analysis?.recommendations ?? []

  return (
    <>
      <section className="panel detail-header-panel">
        <div className="detail-header">
          <div className="detail-identity">
            <button
              className="back-button"
              type="button"
              onClick={onBack}
            >
              ← Mission overview
            </button>
            <div>
              <p className="eyebrow">Astronaut monitoring</p>
              <h2>{name}</h2>
              <div className="detail-meta">
                {name !== astronautId && <span>{astronautId}</span>}
                {mission && <span>{mission}</span>}
                {latest?.recorded_at && (
                  <span>
                    Last reading {formatDate(latest.recorded_at)}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="detail-status">
            <span className={statusClass(severity)}>
              {SEVERITY_LABEL[severity] ?? severity}
            </span>
            <span className="last-updated">
              Updated {formatRelativeTime(latest?.recorded_at)}
            </span>
          </div>
        </div>
      </section>

      {requiresReview && (
        <section className="alert alert-review">
          <strong>Review recommended.</strong> The latest reading
          exceeds at least one personalised threshold or is flagged by
          the ML model.
        </section>
      )}

      {error && (
        <section className="alert alert-error">
          <strong>Analysis unavailable.</strong> {error}
        </section>
      )}

      {loading && !analysis && (
        <section className="panel placeholder">
          Loading astronaut analysis…
        </section>
      )}

      {analysis && (
        <>
          <section className="summary-grid">
            <SummaryCard
              label="Baseline"
              value={
                baseline?.version
                  ? `Version ${baseline.version}`
                  : 'None'
              }
              note={`${baseline?.usable_count ?? 0}/${
                baseline?.metric_count ?? 0
              } usable · ${baseline?.window_days ?? '—'} day window`}
            />
            <SummaryCard
              label="Rule alerts"
              value={summary?.anomaly?.alert_count ?? 0}
              note={`Highest severity: ${
                summary?.anomaly?.highest_severity ?? '—'
              }`}
            />
            <SummaryCard
              label="ML anomaly model"
              value={ml?.status ?? 'NOT_EVALUATED'}
              note={
                ml?.anomaly_score === null ||
                ml?.anomaly_score === undefined
                  ? 'No score available'
                  : `Score ${formatNumber(ml.anomaly_score, 3)}`
              }
            />
            <SummaryCard
              label="Data freshness"
              value={formatRelativeTime(latest?.recorded_at)}
              note={`${overviewEntry?.reading_count ?? readings.length} readings stored`}
            />
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Current reading</h2>
                <p className="section-note">
                  Source: {latest?.source ?? '—'} ·{' '}
                  {formatDate(latest?.recorded_at)}
                </p>
              </div>
              {latest?.source && (
                <span className={statusClass(latest.source)}>
                  {latest.source}
                </span>
              )}
            </div>

            <div className="metric-grid">
              {Object.entries(latest?.values ?? {}).map(
                ([metric, value]) => {
                  const meta = METRIC_META[metric] ?? {
                    label: metric,
                    unit: '',
                  }
                  const flag = anomalyByMetric[metric]
                  const isFlagged =
                    flag?.evaluated &&
                    flag.severity !== 'NORMAL' &&
                    flag.severity !== 'NOT_EVALUATED'

                  return (
                    <article className="metric-card" key={metric}>
                      <div className="metric-top">
                        <span>{meta.label}</span>
                        {isFlagged && (
                          <span className={statusClass(flag.severity)}>
                            {flag.severity}
                          </span>
                        )}
                      </div>
                      <strong>
                        {formatMetric(value, meta.unit)}
                      </strong>
                      {flag?.baseline_value !== null &&
                        flag?.baseline_value !== undefined && (
                          <span className="metric-delta">
                            {formatDifference(
                              flag.difference,
                              meta.unit,
                            )}{' '}
                            vs baseline
                          </span>
                        )}
                    </article>
                  )
                },
              )}
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Health trends</h2>
                <p className="section-note">
                  Readings over time with the personal baseline
                  reference. Hover a point for its value.
                </p>
              </div>
            </div>

            <div className="chart-controls">
              <div className="metric-tabs">
                {CHART_METRICS.map((metric) => (
                  <button
                    key={metric}
                    type="button"
                    className={
                      metric === chartMetric ? 'active' : ''
                    }
                    onClick={() => setChartMetric(metric)}
                  >
                    {METRIC_META[metric].label}
                  </button>
                ))}
              </div>

              <div className="range-tabs">
                {RANGES.map((range) => (
                  <button
                    key={range.value}
                    type="button"
                    className={
                      range.value === rangeDays ? 'active' : ''
                    }
                    onClick={() => setRangeDays(range.value)}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>

            {readingsLoading ? (
              <p className="chart-empty">Loading reading history…</p>
            ) : readingsError ? (
              <p className="chart-empty">
                Reading history unavailable. {readingsError}
              </p>
            ) : (
              <MetricTrendChart
                readings={readings}
                metric={chartMetric}
                baselineValue={chartBaseline}
                rangeDays={rangeDays}
              />
            )}
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Alerts and insights</h2>
                <p className="section-note">
                  Explainable findings for the latest reading.
                </p>
              </div>
              <button
                className="link-button"
                type="button"
                onClick={onViewAlerts}
              >
                All mission alerts
              </button>
            </div>

            {flagged.length === 0 ? (
              <p className="empty-state">
                No rule-based alerts for this reading. All evaluated
                metrics are within personalised thresholds.
              </p>
            ) : (
              <div className="detail-alert-list">
                {flagged.map((item) => (
                  <article
                    className="detail-alert"
                    key={item.metric}
                  >
                    <div className="alert-card-head">
                      <div>
                        <h3>
                          {item.metric_label} ·{' '}
                          {item.direction ?? 'DEVIATION'}
                        </h3>
                        <p className="observation">
                          {observationFor(item)}
                        </p>
                      </div>
                      <span className={statusClass(item.severity)}>
                        {item.severity}
                      </span>
                    </div>

                    <div className="evidence-grid">
                      <div>
                        <span>Current</span>
                        <strong>
                          {formatMetric(item.current_value, item.unit)}
                        </strong>
                      </div>
                      <div>
                        <span>Baseline</span>
                        <strong>
                          {formatMetric(
                            item.baseline_value,
                            item.unit,
                          )}
                        </strong>
                      </div>
                      <div>
                        <span>Difference</span>
                        <strong>
                          {formatDifference(
                            item.difference,
                            item.unit,
                          )}
                        </strong>
                      </div>
                      <div>
                        <span>Z-score</span>
                        <strong>
                          {formatNumber(item.z_score, 2)}
                        </strong>
                      </div>
                      <div>
                        <span>Baseline</span>
                        <strong>{item.baseline_status}</strong>
                      </div>
                    </div>

                    {contributingFactors(
                      item,
                      flagged,
                      analysis.trends,
                    ).length > 0 && (
                      <>
                        <span className="detail-label">
                          Contributing factors
                        </span>
                        <ul className="factor-list">
                          {contributingFactors(
                            item,
                            flagged,
                            analysis.trends,
                          ).map((factor) => (
                            <li key={factor}>{factor}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Anomaly flags</h2>
                <p className="section-note">
                  Personal Z-scores against the current baseline.
                </p>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Severity</th>
                    <th>Current</th>
                    <th>Baseline</th>
                    <th>Z-score</th>
                    <th>Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((item) => (
                    <tr key={item.metric}>
                      <td>
                        <strong>{item.metric_label}</strong>
                        {item.outside_observed_range && (
                          <span className="table-note">
                            Outside observed range
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={statusClass(item.severity)}>
                          {item.severity}
                        </span>
                      </td>
                      <td>
                        {formatMetric(item.current_value, item.unit)}
                      </td>
                      <td>
                        {formatMetric(
                          item.baseline_value,
                          item.unit,
                        )}
                      </td>
                      <td>
                        {item.z_score === null
                          ? '—'
                          : formatNumber(item.z_score, 2)}
                      </td>
                      <td>{item.direction ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Trend analysis</h2>
                <p className="section-note">
                  Calendar-time regression with 7-day projections.
                </p>
              </div>
            </div>

            <div className="trend-grid">
              {Object.values(analysis.trends).map((trend) => (
                <article className="trend-card" key={trend.metric}>
                  <div className="trend-heading">
                    <strong>{trend.metric_label}</strong>
                    <span className={statusClass(trend.direction)}>
                      {trend.direction}
                    </span>
                  </div>
                  <dl>
                    <div>
                      <dt>Slope / week</dt>
                      <dd>
                        {formatNumber(trend.slope_per_week, 2)}{' '}
                        {trend.unit}
                      </dd>
                    </div>
                    <div>
                      <dt>R²</dt>
                      <dd>
                        {formatNumber(trend.r_squared, 2)}
                      </dd>
                    </div>
                    <div>
                      <dt>7-day projection</dt>
                      <dd>
                        {formatMetric(
                          trend.projected_value,
                          trend.unit,
                        )}
                      </dd>
                    </div>
                  </dl>
                  {!trend.reliable &&
                    trend.direction === 'STABLE' && (
                      <p className="trend-note">Weak model fit.</p>
                    )}
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>ML anomaly model</h2>
                <p className="section-note">
                  Personal Isolation Forest trained on this
                  astronaut&apos;s readings.
                </p>
              </div>
              <span className={statusClass(ml?.status)}>
                {ml?.status ?? 'NOT_EVALUATED'}
              </span>
            </div>

            <div className="ml-grid">
              <div>
                <span className="detail-label">Anomaly score</span>
                <strong>
                  {ml?.anomaly_score === null ||
                  ml?.anomaly_score === undefined
                    ? '—'
                    : formatNumber(ml.anomaly_score, 3)}
                </strong>
              </div>
              <div>
                <span className="detail-label">Decision score</span>
                <strong>
                  {ml?.decision_score === null ||
                  ml?.decision_score === undefined
                    ? '—'
                    : formatNumber(ml.decision_score, 3)}
                </strong>
              </div>
              <div>
                <span className="detail-label">Training samples</span>
                <strong>{ml?.model?.sample_count ?? '—'}</strong>
              </div>
              <div>
                <span className="detail-label">In sample</span>
                <strong>{ml?.in_sample ? 'Yes' : 'No'}</strong>
              </div>
            </div>

            {ml?.reason && (
              <p className="section-note">{ml.reason}</p>
            )}

            {ml?.top_deviating_metrics?.length > 0 && (
              <div className="deviation-list">
                {ml.top_deviating_metrics.map((item) => (
                  <article key={item.metric}>
                    <span>{item.metric_label}</span>
                    <strong>
                      {formatMetric(item.value, item.unit)}
                    </strong>
                    <span>
                      Z {formatNumber(item.z_score, 2)}
                    </span>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Recommended actions</h2>
                <p className="section-note">
                  Decision support attached to this analysis.
                </p>
              </div>
            </div>

            {recommendations.length > 0 ? (
              <ul className="recommendation-list">
                {recommendations.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            ) : (
              <p className="empty-state">
                No recommendations are attached to this analysis yet.
              </p>
            )}
          </section>

          {analysis.warnings.length > 0 && (
            <section className="panel warnings">
              <h2>Analysis notes</h2>
              <ul>
                {analysis.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </>
  )
}
