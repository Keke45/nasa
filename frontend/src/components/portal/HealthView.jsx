import {
  formatRelativeTime,
  METRIC_META,
} from '../../lib/format'
import {
  buildInsights,
  healthStatusFor,
} from '../../lib/portal'
import {
  HistoryTable,
  InfoNote,
  InsightCard,
  MeasurementCard,
  Panel,
  SectionHeading,
  StatusPill,
} from './shared'

const ALL_METRICS = Object.keys(METRIC_META)

export default function HealthView({
  analysis,
  readings,
  onNavigate,
}) {
  const status = healthStatusFor(analysis)
  const insights = buildInsights(analysis)
  const latest = analysis.reading
  const baseline = analysis.baseline

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="My health"
          title="Latest health measurements"
          description={`Recorded ${formatRelativeTime(
            latest.recorded_at,
          )} · Source: ${latest.source}`}
          action={
            <StatusPill
              severity={status.severity}
              label={status.label}
            />
          }
        />

        <div className="measurement-grid">
          {ALL_METRICS.map((metric) => (
            <MeasurementCard
              key={metric}
              metric={metric}
              analysis={analysis}
            />
          ))}
        </div>

        <InfoNote>
          Status labels compare the latest reading with your own
          personal baseline. They are not a clinical diagnosis.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Assessment"
          title="What this means for you"
          description={status.description}
        />

        <div className="health-summary-grid">
          <article className="health-summary-card">
            <span>Personal baseline</span>
            <strong>
              {baseline.version
                ? `Version ${baseline.version}`
                : 'Not established'}
            </strong>
            <p>
              {baseline.usable_count}/{baseline.metric_count}{' '}
              metrics available · {baseline.window_days ?? '—'} day
              window
            </p>
          </article>
          <article className="health-summary-card">
            <span>Rule-based alerts</span>
            <strong>{analysis.summary.anomaly.alert_count}</strong>
            <p>
              Highest severity:{' '}
              {analysis.summary.anomaly.highest_severity}
            </p>
          </article>
          <article className="health-summary-card">
            <span>Pattern check</span>
            <strong>{analysis.ml_anomaly.status}</strong>
            <p>
              {analysis.ml_anomaly.reason ||
                'Personal anomaly model result for this reading.'}
            </p>
          </article>
          <article className="health-summary-card">
            <span>Data freshness</span>
            <strong>
              {formatRelativeTime(latest.recorded_at)}
            </strong>
            <p>{readings.length} measurements stored</p>
          </article>
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Intelligence"
          title="My health insights"
          description="Understandable findings from your latest assessment."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('insights')}
            >
              View all
            </button>
          }
        />

        <div className="insight-list">
          {insights.slice(0, 2).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="History"
          title="Recent measurements"
          description="Your latest recorded health readings."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('history')}
            >
              Full history
            </button>
          }
        />

        <HistoryTable readings={readings} limit={8} />
      </Panel>
    </>
  )
}
