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
      const original = link.textContent.trim()
      link.innerHTML = `<span class="topic-index__label"><span class="topic-index__number">${index + 1}</span><span>${original}</span></span>`
    })
  }
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
  const archiveHeading = Array.from(pageContent.querySelectorAll("h2, h3")).find(
    (node) => node.textContent.trim().toLowerCase() === "monthly archives"
  )

  if (!totalParagraph || !archiveHeading) return false

  const totalText = totalParagraph.textContent.trim()
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
  banner.appendChild(metaStrip)
  banner.appendChild(
    createQuickSectionNav([
      { href: "#monthly-archives", label: "Monthly Archives" },
    ])
  )
  banner.appendChild(
    createLinks([
      { href: "./index.html", label: "Back to Home" },
      { href: "./paper_list.html", label: "Open Full Paper List" },
      { href: "./analytics/", label: "View Analytics" },
    ])
  )

  pageContent.insertBefore(banner, heading)
  heading.remove()
  totalParagraph.remove()
  archiveHeading.id = "monthly-archives"
  return true
}

function enhanceMonthlyPage(pageContent, heading) {
  if (!pageContent.querySelector("table")) return false
  const title = heading.textContent.trim()
  const parentDir = window.location.pathname.replace(/[^/]+$/, "")
  const parentIndex = parentDir.endsWith("/") ? "../" : "./"
  const banner = document.createElement("section")
  banner.className = "hero-banner"
  banner.innerHTML = `
    <h2>${title}</h2>
    <p class="lede">Daily paper entries for this monthly archive, optimized for desktop scanning and mobile reading.</p>
  `
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
      { href: `${parentIndex}../paper_list.html`, label: "Open Full Paper List" },
      { href: `${parentIndex}../analytics/`, label: "View Analytics" },
    ])
  )
  pageContent.insertBefore(banner, heading)
  heading.remove()
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
        "A topic-organized research index tuned for scanning: compact navigation above, denser paper tables below, and direct paths into analytics or monthly archives."
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
  wrapTables()
  enhanceArchiveLists()
  enhanceTopicIndex()
  decorateContent()
})
