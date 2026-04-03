---
layout: default
---

# 论文列表可视化与导出（Analytics）设计文档

- 日期：2026-03-31
- 状态：草案（已确认关键口径：code_url 覆盖率、Top 第一作者）
- 目标仓库：paper-list（当前为 Jekyll GitHub Pages + Markdown 生成）

## 1. 背景与目标

本项目已能按 Topic 抓取 arXiv 论文并落盘到 `docs/data/YYYY-MM.json`，再生成：
- GitHub Pages 首页：`docs/index.md`
- 各 Topic 总览页：`docs/<Topic>.md`（含按月分卷链接）
- 各 Topic 的月报页：`docs/<Topic>/<YYYY-MM>.md`

新增需求：在不破坏当前生成链路的前提下，增加“不同领域（Topic）+ 不同时间粒度（日/月）”的统计图表与数据导出，并在 GitHub Pages 提供轻量交互页，同时在 Markdown 里提供稳定可渲染的静态图。

### 1.1 成功标准（Success Criteria）
- **都要**：同时支持
  1) GitHub Pages 交互页（Analytics Dashboard）
  2) Markdown 内嵌静态图（PNG/SVG）
  3) 统计数据导出（CSV/JSON）
- 指标覆盖：
  - 按时间的数量趋势（日 + 月）
  - 领域热度排行（时间窗内 Top Topics / 增长）
  - 作者活跃度（第一作者 TopN，第一阶段）
  - 代码链接覆盖率（`code_url` 覆盖率；翻译/阅读链接不做“覆盖率”主指标）
- 新增 Topic：在现有 Topic 之外允许继续扩展 `config.yaml` 并自动体现在统计与图表中。

## 2. 约束与非目标（Non-goals）

### 2.1 约束
- 现有站点是 **Jekyll**（`docs/_config.yml`），应避免引入需要构建的前端框架（如 Next/Vite）。
- GitHub Actions/Pages 运行环境不稳定项（联网校验、复杂构建）尽量减少；尽量使用“离线聚合 + 静态产物”。
- 当前数据字段中 `translate_url/read_url/pdf_url` 由系统默认构造，覆盖率趋近 100%，不作为主分析指标。

### 2.2 非目标
- 不在第一阶段实现“按周（week）”粒度（可作为后续扩展）。
- 不在第一阶段实现“全作者列表/机构识别”的精细统计（后续可通过新增字段实现）。
- 不实现在线实时数据抓取/后端服务；所有数据从 `docs/data` 预计算生成。

## 3. 数据源与字段说明

### 3.1 输入数据源
来自现有存储：
- `docs/data/*.json`（按月分片），结构由 `utils.storage.load_paper_store()` 归一化为：
  - `data[topic][paper_id] -> record`

`record`（通过 `utils.paper_links.ensure_paper_record()` 归一化）主要字段：
- `date`：`YYYY-MM-DD`
- `title`
- `authors`：当前为“第一作者 + et.al.”字符串（第一阶段按“第一作者”统计）
- `arxiv_id`
- `pdf_url`
- `translate_url`
- `read_url`
- `code_url`：可空

### 3.2 指标定义

#### 3.2.1 论文数量（Counts）
对给定时间粒度 `g ∈ {day, month}`：
- `count(topic, t)`：Topic 在时间桶 `t` 的论文数

#### 3.2.2 代码覆盖率（Code Coverage）
对给定 Topic、时间桶 `t`：
- `code_covered = #papers where code_url is not null`
- `total = #papers`
- `code_coverage = code_covered / total`（若 `total=0` 则该桶为空或 coverage 置为 `null`）

#### 3.2.3 作者活跃度（Top First Authors）
第一阶段的“作者”定义为：
- `first_author = authors` 字段中 `et.al.` 前的作者名（粗粒度）

统计：
- 在时间窗 `[start, end]` 内按 `first_author` 计数，输出 TopN。

> 备注：由于当前仅保存第一作者字符串，本阶段明确输出为 “Top 第一作者榜”。后续如要更准确统计，可新增 `authors_full`（完整作者列表）字段并向后兼容。

## 4. 输出物（Artifacts）

在 `docs/` 下新增 analytics 目录，结构如下：

```
docs/
  analytics/
    index.html                # 交互页（纯 HTML/JS）
    assets/
      app.js                  # 交互逻辑（可拆分为多个文件）
      app.css                 # 样式
    data/
      daily_counts.json
      monthly_counts.json
      code_coverage_daily.json
      code_coverage_monthly.json
      topic_rank_{range}.json
      top_authors_{range}.json
      meta.json               # 主题列表、日期范围、生成时间等
      *.csv                   # 对应 CSV 导出（可选：与 JSON 同名）
    charts/
      trend_daily.png
      trend_monthly.png
      topic_rank.png
      code_coverage_trend.png
      top_authors.png
```

### 4.1 导出数据格式（建议的 JSON schema）

#### `meta.json`
```json
{
  "generated_at": "2026-03-31T00:00:00Z",
  "topics": ["Classification", "Object Detection"],
  "min_date": "2024-02-01",
  "max_date": "2026-03-31",
  "granularities": ["day", "month"],
  "default_range_days": 90,
  "default_range_months": 12
}
```

#### `daily_counts.json` / `monthly_counts.json`
行式结构（便于前端筛选与 CSV 对齐）：
```json
[
  {"topic": "LLM", "date": "2026-03-01", "count": 12},
  {"topic": "LLM", "date": "2026-03-02", "count": 8}
]
```
`monthly_counts.json` 的 `date` 使用 `YYYY-MM`。

#### `code_coverage_daily.json` / `code_coverage_monthly.json`
```json
[
  {"topic": "LLM", "date": "2026-03-01", "total": 12, "code_covered": 5, "code_coverage": 0.4167}
]
```

#### `topic_rank_{range}.json`
range 建议固定内置（第一阶段）：
- `last_30d`：最近 30 天（日粒度窗口的排行）
- `last_90d`：最近 90 天
- `last_12m`：最近 12 个月（月粒度窗口的排行）
- `ytd`：Year-to-date（从当年 01-01 至今）

可选扩展：
- `custom_{start}_{end}`：自定义窗口（如前端支持自定义日期范围，建议在前端计算排行；或离线生成一份自定义窗口导出）。
```json
[
  {"topic": "LLM", "count": 320, "rank": 1},
  {"topic": "Multimodal", "count": 210, "rank": 2}
]
```

#### `top_authors_{range}.json`
```json
[
  {"author": "Alice Zhang", "count": 18, "rank": 1}
]
```

### 4.2 Markdown 静态图嵌入点
- `README.md`：可选放 1-2 张“全局趋势/覆盖率”缩略图 + 指向 Analytics 页链接
- `docs/index.md`：顶部新增 “Analytics” 入口（链接到 `analytics/`），并可嵌入 2-4 张关键图
- （可选）单 Topic 总览页 `docs/<Topic>.md`：嵌入该 Topic 的趋势/覆盖率图（第二阶段）

## 5. 交互页（GitHub Pages）设计

### 5.1 页面目标
提供轻量交互：
- 选择时间粒度：日 / 月
- 选择 Topic：多选（默认全选或常用集合）
- 选择时间范围：默认最近 N 天（如 90 天）或最近 N 月（如 12 月）

展示模块：
1) 趋势图：按时间的 count（可按 Topic 堆叠或多折线）
2) Topic 排行：当前时间窗内 Top Topics
3) Code Coverage 趋势：覆盖率折线（按 Topic 或整体）
4) Top First Authors：当前时间窗 TopN

### 5.2 技术实现
- 采用纯 HTML + 原生 JS 或轻量库（例如 ECharts/Chart.js）
  - 注意：需要兼容 GitHub Pages（静态文件）与离线加载。
- 数据来源：`docs/analytics/data/*.json`
- 不依赖后端 API。

> 库选择在实现计划阶段最终敲定（优先：ECharts，体积与能力均衡；或 Chart.js 更轻量）。

## 6. 生成与集成流程

### 6.1 新增生成步骤
在现有更新流程（`get_paper.py` 或 `scripts/fetch_monthly.py`）之后，新增一个“analytics 构建”步骤：
1) 从 `docs/data` 读取并归一化
2) 生成聚合数据到 `docs/analytics/data`
3) 生成静态图到 `docs/analytics/charts`
4) 轻量更新 `docs/index.md`（或在其顶部插入/追加 Analytics 区块）

建议新增脚本入口（名称可在实现阶段微调）：
- `scripts/build_analytics.py`
  - 输入：`--store docs/data`
  - 输出：`--out docs/analytics`
  - 默认范围：`--default_days 90 --default_months 12`
  - 排行窗口：内置 `last_30d/last_90d/last_12m/ytd`

### 6.2 增量更新策略（可选）
第一阶段可全量重算（以稳定为主）；后续可利用：
- 输入数据按月分片（`docs/data/YYYY-MM.json`）
做增量聚合，减少 CI 时间。

## 7. 新增 Topic 的配置与兼容

### 7.1 新增 Topic
通过修改 `config.yaml` 的 `keywords` 增加新的 Topic 与 filters。

### 7.2 自动适配
Analytics 聚合时从 `docs/data` 的顶层 key 读取 topic 列表，**不手写白名单**，保证新增 Topic 自动进入导出与图表。

## 8. 质量与测试策略

- 单元测试（建议）：
  - 聚合函数：输入一小段固定 JSON，验证 counts / coverage / top authors 输出稳定
- 端到端（建议）：
  - 在本地运行 `get_paper.py`（或使用已有样例 json），再运行 analytics 构建脚本，检查产物路径齐全
- 回归风险控制：
  - 任何新增逻辑不应改变 `docs/data` 的既有结构
  - 不应影响 `utils.json_tools.json_to_md` 生成 Markdown 的主流程

## 9. 风险与缓解

1) **作者统计不精确**：当前仅第一作者字符串
   - 缓解：明确输出为“Top 第一作者”；后续通过新增字段升级
2) **图表库体积/兼容性**：
   - 缓解：优先选稳定 CDN-free 方案（将库文件 vendoring 到 `docs/analytics/assets/`）
3) **覆盖率指标误解**：
   - 缓解：只展示 code_url 覆盖率；translate/read 不做覆盖率主图

## 10. 里程碑拆分（建议）

- M1：生成聚合数据（JSON+CSV）+ 生成 4-5 张静态图 + 在 `docs/index.md` 增加入口
- M2：交互页（读取 JSON、筛选、切换日/月、展示趋势/排行/覆盖率/作者）
- M3（可选）：作者字段升级（保存完整作者列表）、Topic 级别的小卡片与 drill-down
