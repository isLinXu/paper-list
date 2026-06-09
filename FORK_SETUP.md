# 🍴 Fork Setup Guide

**Fork 后 3 步完成配置，即可获得属于你自己的全自动 arXiv 论文追踪系统。**

---

## ⚡ 快速 Checklist

- [ ] Step 1 — 运行 `make setup`（自动配置一切）
- [ ] Step 2 — 在 GitHub Actions 中启用 workflow
- [ ] Step 3 — 运行 `make health-check` 验证

---

## Step 1 — 一键配置

### 方式 A：交互式向导（推荐）

```bash
pip install -r requirements.txt
python scripts/setup_fork.py
```

向导会自动完成：
- ✅ 从 git remote 检测你的 GitHub 用户名
- ✅ 更新 `config.yaml` 中的 `user_name` 和 `repo_name`
- ✅ **自动更新 `docs/_config.yml`** 中的上游 URL（不再需要手动改！）
- ✅ **从模板创建 `.env` 文件**（预填充你的用户名和仓库名）
- ✅ 选择预设 profile（minimal / vision / nlp_llm / robotics / full）
- ✅ 引导你自定义研究主题
- ✅ 检查 GitHub Token 配置

### 方式 B：非交互式（CI/CD 友好）

```bash
python scripts/setup_fork.py --non-interactive
# 或
make init-fork
```

自动从 git remote 检测并配置一切，无需任何输入。

### 方式 C：直接应用 Profile

```bash
python scripts/setup_fork.py --profile minimal   # 3 个核心主题
python scripts/setup_fork.py --profile vision     # 12 个 CV 主题
python scripts/setup_fork.py --profile nlp_llm    # 8 个 NLP/LLM 主题
python scripts/setup_fork.py --profile robotics   # 9 个机器人主题
python scripts/setup_fork.py --profile full       # 全部 20+ 主题
```

---

## Step 2 — 启用 GitHub Actions Workflow

> ⚠️ **重要**：GitHub 对 fork 的仓库默认**禁用定时任务 (scheduled workflows)**

1. 进入你 fork 的仓库页面
2. 点击顶部导航 **"Actions"** 标签
3. 如果看到提示 "Workflows aren't being run on this forked repository"，点击 **"I understand my workflows, go ahead and enable them"**
4. 分别找到 **"Run Arxiv Papers Daily"** 和 **"Run Update Paper Links Weekly"**，确认它们已启用

手动触发测试（推荐首次验证）：
1. 在 Actions 页面选中 **"Run Arxiv Papers Daily"**
2. 点击 **"Run workflow"** 按钮
3. 在下拉中可以指定 `start_date` 和 `end_date`（首次建议填最近 3 天）

---

## Step 3 — 验证配置

### 全面健康检查

```bash
python scripts/health_check.py           # 快速诊断
python scripts/health_check.py --verbose # 详细输出
python scripts/health_check.py --fix     # 自动修复已知问题
# 或
make health-check
make doctor
```

检查内容包括：
- ✅ 配置文件语法和逻辑校验
- ✅ API 连通性（Papers with Code、arXiv、GitHub）
- ✅ 数据完整性（JSON 分片、论文数量、时效性）
- ✅ 运行环境（Python 版本、依赖包、.env、git remote）
- ✅ GitHub Pages 就绪状态（`_config.yml`、Jekyll）

### 仅校验配置

```bash
python scripts/validate_config.py
# 或
make validate
```

### 本地测试抓取

```bash
# 抓最近一周
python get_paper.py --start_date 2026-06-01 --end_date 2026-06-08
# 或
make fetch-week
```

---

## 环境变量配置

### 方式 1：.env 文件（推荐）

```bash
cp .env.example .env
# 编辑 .env 填入你的值
```

`.env` 文件会被 `utils/configs.py` **自动加载**，无需手动 export。

### 方式 2：Shell 环境变量

```bash
export PAPER_LIST_USER=your-username
export PAPER_LIST_REPO=your-paper-list
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### 方式 3：GitHub Actions Secrets

在仓库 Settings > Secrets and variables > Actions 中添加。

> **优先级**：Shell 环境变量 > `.env` 文件 > `config.yaml`

---

## 添加自定义研究主题

1. 在 `config.yaml` 的 `keywords` 段添加新 topic：

```yaml
keywords:
  # 新增你的 topic
  "My Custom Topic":
    filters: ["keyword1", "keyword2 phrase", "keyword3"]
```

2. 将新 topic 添加到 `config.yaml` 的 `topic_groups`，使其出现在 GitHub Pages 的分组导航中：

```yaml
topic_groups:
  - ["My Group Name", "My Lane Title", "theme-card--vision",
     ["My Custom Topic", ...]]
```

> 如果不修改 `topic_groups`，新 topic 会出现在页面底部，功能正常但没有分组。

3. 运行校验：`python scripts/validate_config.py`

---

## 常见问题

**Q: Workflow 运行成功但没有新论文？**  
A: 检查 `config.yaml` 中的 `start_date` 是否覆盖了正确的日期范围，也可能是该关键词在该日期范围内确实没有新论文。

**Q: GitHub Pages 站点没有更新？**  
A: 确保仓库 Settings > Pages 中的 Source 设为 `main` 分支的 `/docs` 文件夹。同时检查 `docs/_config.yml` 是否还有上游 URL 残留（运行 `make doctor` 自动修复）。

**Q: 遇到 GitHub API rate limit 错误？**  
A: 在 `.env` 文件中设置 `GITHUB_TOKEN=ghp_xxxxx`，或在 GitHub 仓库中添加 secret。

**Q: 本地运行报 `arxiv` 模块未找到？**  
A: 执行 `pip install -r requirements.txt` 安装依赖。

**Q: `docs/_config.yml` 还是指向上游仓库？**  
A: 运行 `python scripts/setup_fork.py` 或 `make doctor` 自动修复。

**Q: 如何临时关闭某个主题？**  
A: 在 `config.yaml` 中给该主题加 `enabled: false`：
```yaml
"Object Detection":
  enabled: false
  filters: ["Object Detection"]
```

**Q: 如何查看哪些 filter 没有命中任何论文？**  
A: 运行 `make audit-zombie` 查看"僵尸"过滤器。
