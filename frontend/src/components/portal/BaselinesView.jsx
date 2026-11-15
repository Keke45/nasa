import {
  formatDate,
  formatMetric,
  METRIC_META,
} from '../../lib/format'
import {
  anomalyFor,
  assessmentFor,
  formatDelta,
  latestValue,
} from '../../lib/portal'
import {
  InfoNote,
  Panel,
  SectionHeading,
  StatusPill,
} from './shared'

const ALL_METRICS = Object.keys(METRIC_META)

export default function BaselinesView({ analysis }) {
  const baseline = analysis.baseline

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="My baselines"
          title="Your personal reference range"
          description="Baselines are calculated from your own recent health measurements. They are not population averages."
        />

        <div className="baseline-summary-grid">
          <article>
            <span>Baseline version</span>
            <strong>
              {baseline.version ? `Version ${baseline.version}` : '—'}
            </strong>
            <p>
              {baseline.established_at
                ? `Established ${formatDate(
                    baseline.established_at,
                  )}`
                : baseline.version
                  ? 'Active personal baseline'
                  : 'Not yet established'}
            </p>
          </article>
          <article>
            <span>Reference window</span>
            <strong>{baseline.window_days ?? '—'} days</strong>
            <p>Recent measurements used for comparison</p>
          </article>
          <article>
            <span>Usable metrics</span>
            <strong>
              {baseline.usable_count}/{baseline.metric_count}
            </strong>
            <p>Measurements with enough data</p>
          </article>
          <article>
            <span>Latest reading</span>
            <strong>
              {formatDate(analysis.reading.recorded_at)}
            </strong>
            <p>{analysis.reading.source} source</p>
          </article>
        </div>

        <InfoNote>
          Your baseline moves with your recent health data. A reading
          can fall outside the expected range without being a medical
          problem; the intelligence engine uses this range to decide
          what to flag.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Measurements"
          title="All personal baselines"
          description="Latest value, established baseline, difference and current assessment."
        />

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Measurement</th>
                <th>Baseline</th>
                <th>Latest</th>
                <th>Difference</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {ALL_METRICS.map((metric) => {
                const meta = METRIC_META[metric]
                const anomaly = anomalyFor(analysis, metric)
                const assessment = assessmentFor(analysis, metric)

                return (
                  <tr key={metric}>
                    <td>
                      <strong>{meta.label}</strong>
                      <span className="table-subtext">
                        {metric}
                      </span>
                    </td>
                    <td>
                      {formatMetric(
                        anomaly?.baseline_value,
                        meta.unit,
                      )}
                    </td>
                    <td>
                      {formatMetric(
                        latestValue(analysis, metric),
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

      <Panel>
        <SectionHeading
          title="How to read your baseline"
          description="Three things to keep in mind."
        />
        <div className="baseline-guide">
          <article>
            <strong>It is personal</strong>
            <p>
              Your baseline reflects your own measurements, not the
              crew average or a general population reference.
            </p>
          </article>
          <article>
            <strong>It is a comparison</strong>
            <p>
              The latest reading is compared with the range your body
              has recently established.
            </p>
          </article>
          <article>
            <strong>It is not a diagnosis</strong>
            <p>
              A flagged value means the measurement is unusual for
              you. Mission medical personnel interpret what it means.
            </p>
          </article>
        </div>
      </Panel>
    </>
  )
}
