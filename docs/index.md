---
layout: default
title: Paper Arxiv Daily
---
<div class="page-home">
  <section class="hero hero--editorial">
    <div class="hero__grid">
      <div>
        <span class="eyebrow">Daily arXiv Watch</span>
        <h1>Paper Arxiv Daily</h1>
        <p>
          A curated research surface for following fast-moving arXiv output across computer vision,
          multimodal systems, large language models, and adjacent machine learning tracks.
        </p>
        <div class="page-meta">
          <span class="pill">Updated 2026.04.03</span>
          <span class="pill">17 core tracks</span>
          <span class="pill">8-hour automation cycle</span>
        </div>
        <div class="hero__actions">
          <a class="button button--primary" href="#topics">Browse Topics</a>
          <a class="button button--ghost" href="#timeline">Explore Timeline</a>
          <a class="button button--ghost" href="analytics/">Open Analytics</a>
        </div>
      </div>

      <aside class="hero-panel">
        <span class="hero-panel__label">Research Pulse</span>
        <div class="hero-panel__stat">
          <strong>2024 → 2026</strong>
          <span>A multi-year archive with enough depth to reveal theme evolution instead of just daily noise.</span>
        </div>
        <div class="hero-panel__rail">
          <div class="hero-panel__rail-item">
            <span>2024</span>
            <p>Foundation archive and baseline topics.</p>
          </div>
          <div class="hero-panel__rail-item">
            <span>2025</span>
            <p>Cross-modal expansion and broader model families.</p>
          </div>
          <div class="hero-panel__rail-item">
            <span>2026</span>
            <p>Live intake for the newest papers and code signals.</p>
          </div>
        </div>
      </aside>
    </div>
  </section>

  <section class="signal-strip">
    <article class="signal-card">
      <span class="signal-card__label">Scan</span>
      <h3>Theme-first browsing</h3>
      <p>Start from grouped research families instead of diving straight into a flat list of links.</p>
    </article>
    <article class="signal-card">
      <span class="signal-card__label">Track</span>
      <h3>Timeline awareness</h3>
      <p>Use time as a design layer, not just metadata, so topic momentum is easier to perceive.</p>
    </article>
    <article class="signal-card">
      <span class="signal-card__label">Read</span>
      <h3>Dense but calm tables</h3>
      <p>Long reading surfaces stay usable because the heavy information is visually tiered.</p>
    </article>
  </section>

  <section id="timeline">
    <div class="section-title">
      <h2>Research Timeline</h2>
      <p>
        The site works best when it behaves like a visual research timeline: broad archive coverage,
        live updates, and clear routes from scanning to deep reading.
      </p>
    </div>
    <div class="timeline-grid timeline-grid--editorial">
      <article class="timeline-card">
        <span class="timeline-card__year">2024</span>
        <h3>Foundation Layer</h3>
        <p>Early archive coverage establishes the baseline for long-running topics like classification, segmentation, depth, and tracking.</p>
      </article>
      <article class="timeline-card">
        <span class="timeline-card__year">2025</span>
        <h3>Topic Expansion</h3>
        <p>Multimodal, generation, LLM, audio, and generalization tracks become easier to compare as the archive density increases.</p>
      </article>
      <article class="timeline-card">
        <span class="timeline-card__year">2026</span>
        <h3>Live Research Radar</h3>
        <p>The latest stream becomes a near-live reading queue, with analytics and archive pages helping you spot momentum and topic shifts.</p>
      </article>
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>Core Entry Points</h2>
      <p>Use these routes when you want the site to feel like a compact research product rather than a raw markdown dump.</p>
    </div>
    <div class="card-grid card-grid--two">
      <article class="section-card">
        <span class="subtle-label">Explore</span>
        <h3>Main Paper Index</h3>
        <p>The complete topic-organized list with daily paper tables, archive navigation, and improved mobile readability.</p>
        <div class="section-card__meta">
          <a class="pill" href="paper_list.html">Open full list</a>
        </div>
      </article>
      <article class="section-card">
        <span class="subtle-label">Analyze</span>
        <h3>Analytics Dashboard</h3>
        <p>Review trend curves, topic rankings, approximate code coverage, and top authors using the interactive dashboard.</p>
        <div class="section-card__meta">
          <a class="pill" href="analytics/">Open analytics</a>
        </div>
      </article>
      <article class="section-card section-card--wide">
        <span class="subtle-label">Workflow</span>
        <h3>Repository Workflow</h3>
        <p>Install dependencies, rerun data generation locally, and adjust tracked keywords through the project configuration.</p>
        <div class="section-card__meta">
          <span class="pill">pip install -r requirements.txt</span>
          <span class="pill">python get_paper.py</span>
          <span class="pill">count_range.py</span>
        </div>
      </article>
    </div>
  </section>

  <section id="topics">
    <div class="section-title">
      <h2>Theme Constellations</h2>
      <p>
        Topics are grouped into visual families so the site feels more like a research atlas and less
        like one undifferentiated list of links.
      </p>
    </div>
    <div class="theme-grid">
      <article class="theme-card theme-card--vision">
        <span class="theme-card__tag">Perception Core</span>
        <h3>Vision Systems</h3>
        <p>Dense, high-frequency topics for tracking visual representation learning and scene parsing.</p>
        <div class="theme-card__links">
          <a href="Classification.html">Classification</a>
          <a href="Object_Detection.html">Object Detection</a>
          <a href="Semantic_Segmentation.html">Semantic Segmentation</a>
          <a href="Anomaly_Detection.html">Anomaly Detection</a>
        </div>
      </article>

      <article class="theme-card theme-card--motion">
        <span class="theme-card__tag">Space, Motion, 3D</span>
        <h3>Dynamics and Geometry</h3>
        <p>Follow movement, depth, pose, and long-horizon understanding across video and embodied settings.</p>
        <div class="theme-card__links">
          <a href="Object_Tracking.html">Object Tracking</a>
          <a href="Action_Recognition.html">Action Recognition</a>
          <a href="Pose_Estimation.html">Pose Estimation</a>
          <a href="Depth_Estimation.html">Depth Estimation</a>
          <a href="Optical_Flow.html">Optical Flow</a>
          <a href="Scene_Understanding.html">Scene Understanding</a>
        </div>
      </article>

      <article class="theme-card theme-card--foundation">
        <span class="theme-card__tag">Foundation Models</span>
        <h3>Generative and Multimodal</h3>
        <p>Track the shift from single-modality pipelines toward general-purpose generation, reasoning, and modality fusion.</p>
        <div class="theme-card__links">
          <a href="Image_Generation.html">Image Generation</a>
          <a href="LLM.html">LLM</a>
          <a href="Multimodal.html">Multimodal</a>
          <a href="Audio_Processing.html">Audio Processing</a>
        </div>
      </article>

      <article class="theme-card theme-card--systems">
        <span class="theme-card__tag">Learning Systems</span>
        <h3>Adaptation and Decision</h3>
        <p>Use these tracks to follow transfer, reasoning structure, policy learning, and graph-based learning systems.</p>
        <div class="theme-card__links">
          <a href="Transfer_Learning.html">Transfer Learning</a>
          <a href="Reinforcement_Learning.html">Reinforcement Learning</a>
          <a href="Graph_Neural_Networks.html">Graph Neural Networks</a>
        </div>
      </article>
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>How To Use It</h2>
      <p>The site is strongest when it works as a layered reading flow: choose a family, enter a topic, then drop into the archive or analytics.</p>
    </div>
    <div class="process-grid">
      <article class="process-card">
        <span class="process-card__step">01</span>
        <h3>Pick a family</h3>
        <p>Use the constellation blocks to decide which part of the research landscape you want to inspect first.</p>
      </article>
      <article class="process-card">
        <span class="process-card__step">02</span>
        <h3>Open a topic</h3>
        <p>Move into a focused topic page where monthly archives provide a more manageable browsing cadence.</p>
      </article>
      <article class="process-card">
        <span class="process-card__step">03</span>
        <h3>Read or analyze</h3>
        <p>Choose between dense raw tables for immediate reading or analytics for trend and author-level pattern spotting.</p>
      </article>
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>Usage Snapshot</h2>
      <p>For local regeneration or customization, the existing workflow remains simple and script-first.</p>
    </div>
    <div class="section-card">
      <h3>Generate locally</h3>
      <p>Install dependencies, run the fetcher, and adjust tracked keywords in <code>config.yaml</code> when needed.</p>
      <pre><code class="language-bash">pip install -r requirements.txt
python get_paper.py
python scripts/count_range.py 2024-01-01 2024-12-31</code></pre>
    </div>
  </section>
</div>
