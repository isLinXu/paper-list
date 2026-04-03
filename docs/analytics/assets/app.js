function initThemeSwitcher() {
  const select = document.getElementById("theme-switcher")
  if (!select) return

  const current = document.documentElement.getAttribute("data-theme") || "editorial"
  select.value = current

  select.addEventListener("change", () => {
    const theme = select.value
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("paper-list-theme", theme)
  })
}

async function fetchJson(path) {
  const r = await fetch(path, { cache: "no-store" })
  if (!r.ok) throw new Error(`Fetch failed: ${path} ${r.status}`)
  return r.json()
}

function uniqSorted(arr) {
  return Array.from(new Set(arr)).sort()
}

function getSelectedOptions(selectEl) {
  return Array.from(selectEl.selectedOptions).map((o) => o.value)
}

function destroyIfExists(chart) {
  if (chart) chart.destroy()
  return null
}

function buildLineDatasets(rows, topics, dateKey, valueKey) {
  // rows: [{topic,date,count}]
  const byTopic = new Map()
  for (const t of topics) byTopic.set(t, new Map())
  for (const r of rows) {
    if (!topics.includes(r.topic)) continue
    byTopic.get(r.topic).set(r[dateKey], r[valueKey])
  }

  const allDates = uniqSorted(rows.map((r) => r[dateKey]))
  const colors = [
    "#70a3ff",
    "#63c6be",
    "#ff8c82",
    "#ffce7c",
    "#c294ff",
    "#7dd7ff",
    "#ffab5e",
    "#8dd19d",
    "#f09cff",
    "#d8e0e6",
  ]

  const datasets = topics.map((t, idx) => {
    const m = byTopic.get(t) || new Map()
    return {
      label: t,
      data: allDates.map((d) => m.get(d) ?? 0),
      borderColor: colors[idx % colors.length],
      backgroundColor: "transparent",
      tension: 0.2,
      borderWidth: 2,
      pointRadius: 0,
    }
  })
  return { labels: allDates, datasets }
}

function buildBarDataset(rows, labelKey, valueKey, title) {
  const labels = rows.map((r) => r[labelKey])
  const data = rows.map((r) => r[valueKey])
  return {
    labels,
    datasets: [
      {
        label: title,
        data,
        backgroundColor: "#2b6cff",
      },
    ],
  }
}

async function main() {
  initThemeSwitcher()
  const meta = await fetchJson("./data/meta.json")
  document.getElementById("meta").textContent = `数据范围：${meta.min_date} ~ ${meta.max_date} · 生成时间：${meta.generated_at}`

  const topicsEl = document.getElementById("topics")
  for (const t of meta.topics) {
    const opt = document.createElement("option")
    opt.value = t
    opt.textContent = t
    opt.selected = true
    topicsEl.appendChild(opt)
  }

  let trendChart = null
  let rankChart = null
  let coverageChart = null
  let authorsChart = null

  async function render() {
    const granularity = document.getElementById("granularity").value
    const preset = document.getElementById("presetRange").value
    const selectedTopics = getSelectedOptions(topicsEl)
    const topicsForChart = (selectedTopics.length ? selectedTopics : meta.topics).slice(0, 10) // 控制可读性

    const countsPath = granularity === "day" ? "./data/daily_counts.json" : "./data/monthly_counts.json"
    const covPath = granularity === "day" ? "./data/code_coverage_daily.json" : "./data/code_coverage_monthly.json"

    const [countsRows, covRows, rankRows, authorRows] = await Promise.all([
      fetchJson(countsPath),
      fetchJson(covPath),
      fetchJson(`./data/topic_rank_${preset}.json`),
      fetchJson(`./data/top_authors_${preset}.json`),
    ])

    // trend (counts)
    trendChart = destroyIfExists(trendChart)
    const trendData = buildLineDatasets(countsRows, topicsForChart, "date", "count")
    trendChart = new Chart(document.getElementById("trendChart"), {
      type: "line",
      data: trendData,
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#dce6ef" } } },
        scales: {
          x: { ticks: { color: "#9fb0bc", maxRotation: 0 }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { ticks: { color: "#9fb0bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    })

    // rank
    rankChart = destroyIfExists(rankChart)
    const topRank = rankRows.slice(0, 20)
    rankChart = new Chart(document.getElementById("rankChart"), {
      type: "bar",
      data: buildBarDataset(topRank, "topic", "count", "Top Topics"),
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9fb0bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { ticks: { color: "#9fb0bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    })

    // coverage (render as line by topic: code_coverage)
    coverageChart = destroyIfExists(coverageChart)
    const covTopics = topicsForChart
    const covData = buildLineDatasets(covRows, covTopics, "date", "code_coverage")
    coverageChart = new Chart(document.getElementById("coverageChart"), {
      type: "line",
      data: covData,
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#dce6ef" } } },
        scales: {
          x: { ticks: { color: "#9fb0bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: {
            ticks: { color: "#9fb0bc" },
            grid: { color: "rgba(255,255,255,0.05)" },
            suggestedMin: 0,
            suggestedMax: 1,
          },
        },
      },
    })

    // authors
    authorsChart = destroyIfExists(authorsChart)
    const topAuthors = authorRows.slice(0, 20)
    authorsChart = new Chart(document.getElementById("authorsChart"), {
      type: "bar",
      data: buildBarDataset(topAuthors, "author", "count", "Top First Authors"),
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9fb0bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { ticks: { color: "#9fb0bc" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    })
  }

  document.getElementById("apply").addEventListener("click", () => {
    render().catch((e) => alert(e.message))
  })

  await render()
}

main().catch((e) => {
  console.error(e)
  alert(e.message)
})
