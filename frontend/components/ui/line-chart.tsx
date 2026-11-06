'use client'

import Chart from 'chart.js/auto'
import { useEffect, useId, useRef } from 'react'

// GOV.UK chart colours: https://brand.design-system.service.gov.uk/colour/charts/
Chart.defaults.color = '#0b0c0c'
Chart.defaults.borderColor = '#cecece'

export type LineChartSeries = {
  label: string
  colour: string
  dash?: number[]
  data: (number | null)[]
}

const round = (value: number) =>
  value.toLocaleString('en-GB', { maximumFractionDigits: 2 })

export function LineChart({
  title,
  labels,
  series,
  integer = false,
  format = round,
}: {
  title: string
  labels: string[]
  series: LineChartSeries[]
  integer?: boolean
  format?: (value: number) => string
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const titleId = useId()
  // The page rebuilds these arrays on every render; only redraw when the values change.
  const key = JSON.stringify({ labels, series })

  useEffect(() => {
    const chart = new Chart(canvas.current!, {
      type: 'line',
      data: {
        labels,
        datasets: series.map(({ label, colour, dash, data }) => ({
          label,
          data,
          borderColor: colour,
          backgroundColor: colour,
          borderDash: dash,
        })),
      },
      options: {
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              ...(integer ? { precision: 0 } : {}),
              callback: (value) => format(Number(value)),
            },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (item) =>
                `${item.dataset.label}: ${format(item.parsed.y ?? 0)}`,
            },
          },
        },
      },
    })
    return () => chart.destroy()
    // format is left out: pages pass a new function each render, and it only changes with the data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, integer])

  return (
    <>
      <h3 id={titleId} className="govuk-heading-m govuk-!-margin-top-7">
        {title}
      </h3>
      <canvas ref={canvas} role="img" aria-labelledby={titleId} />
      <details className="govuk-details govuk-!-margin-top-3">
        <summary className="govuk-details__summary">
          <span className="govuk-details__summary-text">Show data</span>
        </summary>
        <div className="govuk-details__text overflow-x-auto">
          <table className="govuk-table">
            <caption className="govuk-table__caption govuk-table__caption--s">
              {title}
            </caption>
            <thead className="govuk-table__head">
              <tr className="govuk-table__row">
                <th
                  scope="col"
                  className="govuk-table__header govuk-table__header--numeric"
                >
                  Hour
                </th>
                {series.map(({ label }) => (
                  <th
                    key={label}
                    scope="col"
                    className="govuk-table__header govuk-table__header--numeric"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="govuk-table__body">
              {labels.map((label, row) => (
                <tr key={label} className="govuk-table__row">
                  <th
                    scope="row"
                    className="govuk-table__header govuk-table__header--numeric"
                  >
                    {label}
                  </th>
                  {series.map(({ label, data }) => (
                    <td
                      key={label}
                      className="govuk-table__cell govuk-table__cell--numeric"
                    >
                      {data[row] == null ? '–' : format(data[row])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}
