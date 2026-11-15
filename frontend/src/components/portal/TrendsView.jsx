import { useState } from 'react'
import {
  formatMetric,
  formatNumber,
  METRIC_META,
} from '../../lib/format'
import {
  anomalyFor,
  assessmentFor,
  formatDelta,
  latestValue,
  metricStats,
  TREND_METRICS,
} from '../../lib/portal'
import {
  InfoNote,
  Panel,
  RangeTabs,
  SectionHeading,
  StatusPill,
  TrendGrid,
} from './shared'

export default function TrendsView({ analysis, readings }) {
  const [rangeDays, setRangeDays] = useState(30)

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="Health trends"
          title="How your health is changing"
          description="Heart rate, sleep, fatigue and oxygen saturation over time, with your personal baseline for comparison."
          action={<RangeTabs value={rangeDays} onChange={setRangeDays} />}
        />

        <TrendGrid
          analysis={analysis}
          readings={readings}
          metrics={TREND_METRICS}
          rangeDays={rangeDays}
        />

        <InfoNote>
          The dashed line on each chart is your personal baseline.
          Hover any point to see the recorded value.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Direction"
          title="Trend summary"
          description="A simple summary of the direction and projected movement for each key measurement."
        />

        <div className="trend-summary-grid">
          {TREND_METRICS.map((metric) => {
            const meta = METRIC_META[metric]
            const stats = metricStats(analysis, readings, metric)
            const trend = stats.trend

            return (
              <article className="trend-summary-card" key={metric}>
                <div className="trend-summary-head">
                  <strong>{meta.label}</strong>
                  <StatusPill
                    severity={trend?.direction ?? 'NOT_EVALUATED'}
                    label={trend?.direction ?? 'No trend'}
                  />
                </div>
                <dl>
                  <div>
                    <dt>Weekly change</dt>
                    <dd>
                      {trend?.slope_per_week === null ||
                      trend?.slope_per_week === undefined
                        ? '—'
                        : `${formatNumber(
                            trend.slope_per_week,
                            2,
                          )} ${meta.unit}`}
                    </dd>
                  </div>
                  <div>
                    <dt>7-day outlook</dt>
                    <dd>
                      {formatMetric(
                        trend?.projected_value,
                        meta.unit,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Recent average</dt>
                    <dd>
                      {formatMetric(
                        stats.recentAverage,
                        meta.unit,
                      )}
                    </dd>
                  </div>
                </dl>
                {trend?.reliable === false && (
                  <p className="trend-note">
                    The recent pattern is not strong enough for a
                    confident trend conclusion.
                  </p>
                )}
              </article>
            )
          })}
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Comparison"
          title="Latest reading vs personal baseline"
          description="The same comparison used by the intelligence engine."
        />

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Measurement</th>
                <th>Latest</th>
                <th>Personal baseline</th>
                <th>Difference</th>
                <th>Assessment</th>
              </tr>
            </thead>
            <tbody>
              {TREND_METRICS.map((metric) => {
                const meta = METRIC_META[metric]
                const anomaly = anomalyFor(analysis, metric)
                const assessment = assessmentFor(analysis, metric)

                return (
                  <tr key={metric}>
                    <td>
                      <strong>{meta.label}</strong>
                    </td>
                    <td>
                      {formatMetric(
                        latestValue(analysis, metric),
                        meta.unit,
                      )}
                    </td>
                    <td>
                      {formatMetric(
                        anomaly?.baseline_value,
                        meta.unit,
                      )}
                    </td>
                    <td>
                      {formatDelta(anomaly?.difference, meta.unit)}
                    </td>
                    <td>
                      <StatusPill
                        severity={assessment.severity}
                        label={assessment.label}
                      />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  )
}
