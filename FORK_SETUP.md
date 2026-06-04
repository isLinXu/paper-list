# 🍴 Fork Setup Guide

**Fork 后 5 步完成配置，即可获得属于你自己的全自动 arXiv 论文追踪系统。**

---

## ⚡ 快速 Checklist

- [ ] Step 1 — 修改 `config.yaml` 中的用户名和仓库名
- [ ] Step 2 — 修改 `docs/_config.yml` 中的 GitHub Pages 设置
- [ ] Step 3 — 在 GitHub Actions 中启用 workflow
- [ ] Step 4 — （可选）设置 `GITHUB_TOKEN` secret 以提高 API 速率限制
- [ ] Step 5 — 手动触发一次 workflow，验证配置正确

---

## Step 1 — 修改 config.yaml

打开项目根目录的 `config.yaml`，修改顶部 **FORK SETUP** 段：

```yaml
# FORK SETUP 段
user_name: "YOUR_GITHUB_USERNAME"    # 改为你的 GitHub 用户名
repo_name: "paper-list"              # 改为你的仓库名（如果你改过的话）
```

**其他推荐调整：**

| 字段 | 默认值 | 建议 |
|------|--------|------|
| `max_results` | `100` | 首次测试可改为 `20`，稳定后再调大 |
| `start_date` | `null` | 保持 `null`，由 workflow 动态计算 |
| `publish_wechat` | `False` | 若需微信推送则改为 `True` |

---

## Step 2 — 修改 docs/_config.yml

打开 `docs/_config.yml`，修改以下字段指向你的仓库：

```yaml
github:
  repository_url: https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
  zip_url: https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/archive/refs/heads/main.zip
  another_url: https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
```

---

## Step 3 — 启用 GitHub Actions Workflow

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

## Step 4 — （可选）设置 GITHUB_TOKEN Secret

不设置也能运行，但 GitHub API 调用会受到更严格的速率限制（60次/小时 vs 5000次/小时）。

1. 进入仓库 **Settings > Secrets and variables > Actions**
2. 点击 **"New repository secret"**
3. Name: `GITHUB_TOKEN`（注意：实际上 GitHub Actions 自动提供此 token，通常不需要手动设置）

如需提高 GitHub API 限速，可以创建一个 [Personal Access Token (PAT)](https://github.com/settings/tokens) 并设置为 secret：
- Name: `GH_PAT`
- 修改 workflow 中的 `GITHUB_TOKEN: ${{ secrets.GH_PAT }}`

---

## Step 5 — 验证配置

运行验证脚本（确保无报错）：

```bash
pip install -r requirements.txt
python scripts/validate_config.py
```

本地测试抓取（抓最近 2 天）：

```bash
python get_paper.py --start_date $(date -v-2d +%Y-%m-%d) --end_date $(date +%Y-%m-%d)
# macOS 使用 -v-2d；Linux 使用 -d "2 days ago"
```

---

## 添加自定义研究主题

1. 在 `config.yaml` 的 `keywords` 段添加新 topic：

```yaml
keywords:
  # 新增你的 topic
  "My Custom Topic":
    filters: ["keyword1", "keyword2 phrase", "keyword3"]
```

2. （可选）将新 topic 添加到 `utils/json_tools.py` 中的 `TOPIC_GROUPS`，使其出现在 GitHub Pages 的分组导航中：

```python
TOPIC_GROUPS = [
    (
        "My Group Name",
        "My Lane Title",
        "theme-card--vision",
        ["My Custom Topic", ...],
    ),
    # ...
]
```

> 如果不修改 `TOPIC_GROUPS`，新 topic 会出现在页面底部的默认 "Research Track" 区域，功能正常但没有分组。

---

## 常见问题

**Q: Workflow 运行成功但没有新论文？**  
A: 检查 `config.yaml` 中的 `start_date` 是否覆盖了正确的日期范围，也可能是该关键词在该日期范围内确实没有新论文。

**Q: GitHub Pages 站点没有更新？**  
A: 确保仓库 Settings > Pages 中的 Source 设为 `main` 分支的 `/docs` 文件夹。

**Q: 遇到 GitHub API rate limit 错误？**  
A: 参考 Step 4 配置 PAT，或减小 `max_results` 值。

**Q: 本地运行报 `arxiv` 模块未找到？**  
A: 执行 `pip install -r requirements.txt` 安装依赖。
