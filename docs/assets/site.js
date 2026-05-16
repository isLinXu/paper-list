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

function initViewSwitcher() {
  const select = document.getElementById("view-switcher")
  if (!select) return

  const params = new URLSearchParams(window.location.search)
  const current = params.get("view") || document.documentElement.getAttribute("data-view") || "human"
  select.value = current

  select.addEventListener("change", () => {
    const view = select.value
    document.documentElement.setAttribute("data-view", view)
    localStorage.setItem("paper-list-view", view)

    const nextParams = new URLSearchParams(window.location.search)
    if (view === "agent") {
      nextParams.set("view", "agent")
    } else {
      nextParams.delete("view")
    }
    const nextQuery = nextParams.toString()
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}${window.location.hash}`
    window.history.replaceState({}, "", nextUrl)
  })
}

function focusFinderFromShortcut(event) {
  if (event.defaultPrevented) return
  if (event.key !== "/") return

  const active = document.activeElement
  const isTyping =
    active &&
    (active.tagName === "INPUT" ||
      active.tagName === "TEXTAREA" ||
      active.tagName === "SELECT" ||
      active.isContentEditable)
  if (isTyping) return

  const finder = document.querySelector(".finder-panel input")
  if (!finder) return

  event.preventDefault()
  finder.focus()
  finder.select()
}

function wrapTables() {
  const tables = document.querySelectorAll(".page-content table")
  tables.forEach((table) => {
    if (table.parentElement && table.parentElement.classList.contains("table-shell")) return

    const wrapper = document.createElement("div")
    wrapper.className = "table-shell"
    table.parentNode.insertBefore(wrapper, table)
    wrapper.appendChild(table)

    const headers = Array.from(table.querySelectorAll("thead th")).map((th) => th.textContent.trim())
    table.querySelectorAll("tbody tr").forEach((row) => {
      Array.from(row.children).forEach((cell, idx) => {
        const header = headers[idx]
        if (header) {
          cell.setAttribute("data-label", header)
        }
        const normalized = (header || "").toLowerCase()
        if (normalized === "title") {
          cell.classList.add("is-title")
        }
        if (normalized === "pdf" || normalized === "translate" || normalized === "read") {
          cell.classList.add("is-action")
        }
        if (normalized === "code") {
          cell.classList.add("is-code")
        }
        if (cell.textContent.trim().toLowerCase() === "null") {
          cell.textContent = "No code link"
          cell.classList.add("is-empty")
        }
      })
    })
  })
}

function enhanceArchiveLists() {
  const headings = Array.from(document.querySelectorAll(".page-content h3"))
  const archiveHeading = headings.find((heading) => heading.textContent.trim().toLowerCase() === "monthly archives")
  if (!archiveHeading) return

  const nextList = archiveHeading.nextElementSibling
  if (nextList && nextList.tagName === "UL") {
    nextList.classList.add("archive-grid")
  }
}

function enhanceTopicIndex() {
  const headings = Array.from(document.querySelectorAll(".page-content h2, .page-content h3"))
  const indexHeading = headings.find((heading) => heading.textContent.trim().toLowerCase() === "paper list")
  if (!indexHeading) return

  const nextList = indexHeading.nextElementSibling
  if (nextList && (nextList.tagName === "OL" || nextList.tagName === "UL")) {
    nextList.classList.add("topic-index")
    Array.from(nextList.querySelectorAll("li")).forEach((item, index) => {
      const link = item.querySelector("a")
      if (!link) return
      // Skip if already enhanced (has topic-index__number inside)
      if (link.querySelector(".topic-index__number")) return
      const original = link.textContent.trim()
      link.innerHTML = `<span class="topic-index__label"><span class="topic-index__number">${index + 1}</span><span>${original}</span></span>`
    })
  }
}

function buildFinderPanel({ title, hint, placeholder, filter }) {
  const shell = document.createElement("section")
  shell.className = "finder-panel"

  const intro = document.createElement("div")
  intro.className = "finder-panel__intro"
  intro.innerHTML = `<span class="finder-panel__eyebrow">${hint}</span><h3>${title}</h3>`

  const controls = document.createElement("div")
  controls.className = "finder-panel__controls"

  const input = document.createElement("input")
  input.type = "search"
  input.className = "finder-panel__input"
  input.placeholder = placeholder
  input.setAttribute("aria-label", title)

  const status = document.createElement("p")
  status.className = "finder-panel__status"

  controls.appendChild(input)
  shell.appendChild(intro)
  shell.appendChild(controls)
  shell.appendChild(status)

  const update = () => {
    const visibleCount = filter(input.value.trim().toLowerCase())
    status.textContent = input.value.trim()
      ? `${visibleCount} matching entries`
      : "Showing all entries"
  }

  input.addEventListener("input", update)
  update()
  return shell
}

function initTopicFinder() {
  const topicIndex = document.querySelector(".topic-index")
  if (!topicIndex || topicIndex.dataset.finderReady === "true") return

  const items = Array.from(topicIndex.querySelectorAll("li"))
  if (!items.length) return

  const themeCards = Array.from(document.querySelectorAll(".theme-card"))
  const themeLinks = themeCards.flatMap((card) => Array.from(card.querySelectorAll(".theme-card__links a")))
  const explorerCards = Array.from(document.querySelectorAll(".explorer-card--link"))

  const panel = buildFinderPanel({
    title: "Find a topic fast",
    hint: "Quick finder",
    placeholder: "Filter topics like detection, multimodal, llm, rendering...",
    filter: (query) => {
      let visibleCount = 0

      items.forEach((item) => {
        const text = item.textContent.toLowerCase()
        const visible = !query || text.includes(query)
        item.hidden = !visible
        if (visible) visibleCount += 1
      })

      themeLinks.forEach((link) => {
        const visible = !query || link.textContent.toLowerCase().includes(query)
        link.hidden = !visible
      })

      themeCards.forEach((card) => {
        const visibleLinks = card.querySelectorAll(".theme-card__links a:not([hidden])").length
        card.hidden = !!query && visibleLinks === 0
      })

      explorerCards.forEach((card) => {
        card.hidden = false
      })

      return visibleCount
    },
  })

  topicIndex.parentNode.insertBefore(panel, topicIndex)
  topicIndex.dataset.finderReady = "true"
}

function initArchiveFinder() {
  const archiveGrid = document.querySelector(".archive-grid")
  if (!archiveGrid || archiveGrid.dataset.finderReady === "true") return

  const items = Array.from(archiveGrid.querySelectorAll("li"))
  if (!items.length) return

  const panel = buildFinderPanel({
    title: "Jump to a month",
    hint: "Archive filter",
    placeholder: "Filter archive months like 2026-04 or 2025-12...",
    filter: (query) => {
      let visibleCount = 0
      items.forEach((item) => {
        const visible = !query || item.textContent.toLowerCase().includes(query)
        item.hidden = !visible
        if (visible) visibleCount += 1
      })
      return visibleCount
    },
  })

  archiveGrid.parentNode.insertBefore(panel, archiveGrid)
  archiveGrid.dataset.finderReady = "true"
}

function applyPageKind() {
  const pageContent = document.querySelector(".page-content")
  if (!pageContent) return

  let kind = "document"
  if (pageContent.classList.contains("page-home")) {
    kind = "home"
  } else if (document.querySelector(".archive-grid")) {
    kind = "topic"
  } else if (document.querySelector("table")) {
    kind = "monthly"
  }
  document.documentElement.setAttribute("data-page-kind", kind)
}

function createLinks(links) {
  const container = document.createElement("div")
  container.className = "banner-links"
  links.forEach(({ href, label }) => {
    const link = document.createElement("a")
    link.href = href
    link.textContent = label
    container.appendChild(link)
  })
  return container
}

function createQuickSectionNav(pairs) {
  const nav = document.createElement("nav")
  nav.className = "quick-section-nav"
  pairs.forEach(({ href, label }) => {
    const link = document.createElement("a")
    link.href = href
    link.textContent = label
    nav.appendChild(link)
  })
  return nav
}

function enhanceTopicPage(pageContent, heading) {
  const totalParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Total papers:")
  )
  const laneParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Lane:")
  )
  const latestParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Latest archive month:")
  )
  const neighborsParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Topic neighbors:")
  )
  const archiveHeading = Array.from(pageContent.querySelectorAll("h2, h3")).find(
    (node) => node.textContent.trim().toLowerCase() === "monthly archives"
  )

  if (!totalParagraph || !archiveHeading) return false

  const totalText = totalParagraph.textContent.trim()
  const laneText = laneParagraph?.textContent.replace("Lane:", "").trim()
  const latestText = latestParagraph?.textContent.replace("Latest archive month:", "").trim()
  const banner = document.createElement("section")
  banner.className = "hero-banner"
  banner.innerHTML = `
    <h2>${heading.textContent.trim()}</h2>
    <p class="lede">Monthly archive overview for this research track, with direct links into generated paper tables.</p>
  `

  const metaStrip = document.createElement("div")
  metaStrip.className = "meta-strip"
  const totalPill = document.createElement("span")
  totalPill.className = "pill"
  totalPill.textContent = totalText
  metaStrip.appendChild(totalPill)
  if (laneText) {
    const lanePill = document.createElement("span")
    lanePill.className = "pill"
    lanePill.textContent = laneText
    metaStrip.appendChild(lanePill)
  }
  if (latestText) {
    const latestPill = document.createElement("span")
    latestPill.className = "pill"
    latestPill.textContent = latestText
    metaStrip.appendChild(latestPill)
  }
  banner.appendChild(metaStrip)
  if (neighborsParagraph?.innerHTML) {
    const siblingNav = document.createElement("div")
    siblingNav.className = "sibling-nav"
    siblingNav.innerHTML = neighborsParagraph.innerHTML.replace("Topic neighbors:", "").trim()
    banner.appendChild(siblingNav)
  }
  banner.appendChild(
    createQuickSectionNav([
      { href: "#monthly-archives", label: "Monthly Archives" },
    ])
  )
  banner.appendChild(
    createLinks([
      { href: "./index.html", label: "Back to Home" },
      { href: "./paper_list.html", label: "Topics A-Z" },
      { href: "./analytics/", label: "Research Insights" },
    ])
  )

  pageContent.insertBefore(banner, heading)
  heading.remove()
  laneParagraph?.remove()
  totalParagraph.remove()
  latestParagraph?.remove()
  neighborsParagraph?.remove()
  archiveHeading.id = "monthly-archives"
  return true
}

function enhanceMonthlyPage(pageContent, heading) {
  if (!pageContent.querySelector("table")) return false
  const title = heading.textContent.trim()
  const laneParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Topic lane:")
  )
  const monthlyParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Monthly papers:")
  )
  const latestParagraph = Array.from(pageContent.querySelectorAll("p")).find((p) =>
    p.textContent.includes("Latest available archive for this topic:") || p.textContent.includes("This is the latest archive slice for this topic.")
  )
  const parentDir = window.location.pathname.replace(/[^/]+$/, "")
  const parentIndex = parentDir.endsWith("/") ? "../" : "./"
  const banner = document.createElement("section")
  banner.className = "hero-banner"
  banner.innerHTML = `
    <h2>${title}</h2>
    <p class="lede">Daily paper entries for this monthly archive, optimized for desktop scanning and mobile reading.</p>
  `
  const metaStrip = document.createElement("div")
  metaStrip.className = "meta-strip"
  ;[laneParagraph, monthlyParagraph, latestParagraph].forEach((paragraph) => {
    if (!paragraph) return
    const pill = document.createElement("span")
    pill.className = "pill"
    pill.textContent = paragraph.textContent.trim()
    metaStrip.appendChild(pill)
  })
  if (metaStrip.children.length) {
    banner.appendChild(metaStrip)
  }
  const table = pageContent.querySelector("table")
  if (table) {
    table.id = "paper-table"
  }
  banner.appendChild(
    createQuickSectionNav([
      { href: "#paper-table", label: "Jump to Table" },
    ])
  )
  banner.appendChild(
    createLinks([
      { href: parentIndex, label: "Back to Topic Overview" },
      { href: `${parentIndex}../paper_list.html`, label: "Topics A-Z" },
      { href: `${parentIndex}../analytics/`, label: "Research Insights" },
    ])
  )
  pageContent.insertBefore(banner, heading)
  heading.remove()
  laneParagraph?.remove()
  monthlyParagraph?.remove()
  latestParagraph?.remove()
  return true
}

function refineBannerCopy() {
  const heroBanner = document.querySelector(".page-content .hero-banner")
  if (!heroBanner) return

  const heading = heroBanner.querySelector("h2")
  if (!heading) return

  const text = heading.textContent.trim()
  if (text === "Full Paper List") {
    const lede = heroBanner.querySelector(".lede")
    if (lede) {
      lede.textContent =
        "A dense research index tuned for scanning: compact navigation above, denser paper tables below, and quick paths back into the calmer topic-first archive."
    }
  }
}

function refineHomePage() {
  const home = document.querySelector(".page-home")
  if (!home) return

  const featureGrid = home.querySelector(".feature-grid")
  if (featureGrid) {
    featureGrid.remove()
  }
}

function decorateContent() {
  const pageContent = document.querySelector(".page-content")
  if (!pageContent) return

  pageContent.classList.add("rich-content")

  const firstHeading = pageContent.querySelector("h1, h2")
  if (!firstHeading) return

  const firstParagraph = firstHeading.nextElementSibling
  if (firstParagraph && firstParagraph.tagName === "P") {
    firstParagraph.classList.add("lede")
  }

  const headingText = firstHeading.textContent.trim().toLowerCase()
  if (!pageContent.classList.contains("page-home")) {
    const enhancedTopic = enhanceTopicPage(pageContent, firstHeading)
    if (!enhancedTopic) {
      enhanceMonthlyPage(pageContent, firstHeading)
    }
  }

  const firstImage = pageContent.querySelector("img")
  if (firstImage && pageContent.classList.contains("page-home")) {
    firstImage.closest("p")?.remove()
  }

  refineBannerCopy()
  refineHomePage()
}

document.addEventListener("DOMContentLoaded", () => {
  initThemeSwitcher()
  initViewSwitcher()
  wrapTables()
  enhanceArchiveLists()
  enhanceTopicIndex()
  decorateContent()
  applyPageKind()
  initTopicFinder()
  initArchiveFinder()
  document.addEventListener("keydown", focusFinderFromShortcut)
})
