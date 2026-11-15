import { useState } from 'react'
import {
  formatDate,
  formatMetric,
  formatNumber,
  METRIC_META,
} from '../../lib/format'
import {
  assessmentFor,
  buildInsights,
  formatDelta,
  metricStats,
  recommendationFor,
} from '../../lib/portal'
import MetricTrendChart from '../MetricTrendChart'
import PortalIcon from './PortalIcon'
import {
  InfoNote,
  InsightCard,
  Panel,
  RangeTabs,
  SectionHeading,
  StatusPill,
} from './shared'

const CONFIG = {
  sleep_duration: {
    eyebrow: 'Recovery',
    title: 'Sleep monitoring',
    description:
      'Your sleep duration compared with your personal baseline and recent recovery pattern.',
    icon: 'sleep',
    positive:
      'Your recent sleep duration is consistent with your personal baseline.',
  },
  physical_activity: {
    eyebrow: 'Movement',
    title: 'Physical activity',
    description:
      'Your daily activity compared with your personal baseline and recent movement pattern.',
    icon: 'activity',
    positive:
      'Your recent physical activity is consistent with your personal baseline.',
  },
}

function Stat({ label, value, note }) {
  return (
    <article className="metric-stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <p>{note}</p>}
    </article>
  )
}

export default function MetricFocusView({
  metric,
  analysis,
  readings,
  onNavigate,
}) {
  const [rangeDays, setRangeDays] = useState(14)
  const config = CONFIG[metric]
  const meta = METRIC_META[metric]
  const stats = metricStats(analysis, readings, metric)
  const assessment = assessmentFor(analysis, metric)
  const insights = buildInsights(analysis)
  const metricInsight = insights.find(
    (insight) => insight.metric === metric,
  )
  const insight =
    metricInsight || {
      id: metric,
      severity: assessment.severity,
      metric,
      metric_label: meta.label,
      title: config.positive,
      observation:
        'There is no alert for this measurement in your latest assessment.',
      recommendation: recommendationFor(
        metric,
        'DEFAULT',
        assessment.severity,
      ),
      current_value: stats.latest,
      baseline_value: stats.baseline,
      difference: stats.difference,
      unit: meta.unit,
      z_score: null,
    }
  const recentReadings = [...readings].reverse().slice(0, 10)

  return (
    <>
      <Panel>
        <div className="metric-focus-heading">
          <span className="metric-focus-icon">
            <PortalIcon name={config.icon} />
          </span>
          <div>
            <p className="portal-kicker">{config.eyebrow}</p>
            <h1>{config.title}</h1>
            <p className="section-note">{config.description}</p>
          </div>
          <StatusPill
            severity={assessment.severity}
            label={assessment.label}
          />
        </div>

        <div className="metric-stat-grid">
          <Stat
            label="Latest"
            value={formatMetric(stats.latest, meta.unit)}
            note={formatDate(analysis.reading.recorded_at)}
          />
          <Stat
            label="Personal baseline"
            value={formatMetric(stats.baseline, meta.unit)}
            note={`Version ${analysis.baseline.version ?? '—'}`}
          />
          <Stat
            label="7-day average"
            value={formatMetric(stats.recentAverage, meta.unit)}
            note="Recent monitoring period"
          />
          <Stat
            label="Trend"
            value={stats.trend?.direction ?? '—'}
            note={
              stats.trend?.slope_per_week === null ||
              stats.trend?.slope_per_week === undefined
                ? 'No weekly estimate'
                : `${formatNumber(
                    stats.trend.slope_per_week,
                    2,
                  )} ${meta.unit} per week`
            }
          />
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="History"
          title={`${meta.label} over time`}
          description="Hover a point to see its value. The dashed line marks your personal baseline."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('trends')}
            >
              All trends
            </button>
          }
        />

        <div className="portal-toolbar">
          <RangeTabs value={rangeDays} onChange={setRangeDays} />
        </div>

        <div className="metric-focus-chart">
          <MetricTrendChart
            readings={readings}
            metric={metric}
            baselineValue={stats.baseline}
            rangeDays={rangeDays}
          />
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Intelligence"
          title="What this means"
          description="An explanation based on your latest assessment."
        />
        <InsightCard insight={insight} />
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Recent values"
          title={`${meta.label} history`}
          description="Your latest stored readings for this measurement."
        />

        {recentReadings.length === 0 ? (
          <InfoNote>No measurements are available yet.</InfoNote>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>{meta.label}</th>
                  <th>Compared with baseline</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {recentReadings.map((reading) => {
                  const value = reading[metric]
                  const difference =
                    value !== null &&
                    value !== undefined &&
                    stats.baseline !== null
                      ? Number(value) - Number(stats.baseline)
                      : null

                  return (
                    <tr key={reading.id}>
                      <td>{formatDate(reading.recorded_at)}</td>
                      <td>
                        {formatMetric(value, meta.unit)}
                      </td>
                      <td>
                        {formatDelta(difference, meta.unit)}
                      </td>
                      <td>{reading.source}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  )
}
