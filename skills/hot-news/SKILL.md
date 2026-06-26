---
description: Use this skill when collecting and pushing hot news/hot topics from multiple
  Chinese sources. Triggers on phrases like '热点推送', '新闻热点', '热搜汇总', daily news briefing,
  hot topics aggregation. The skill runs a Python script that fetches RSS feeds and
  APIs from 人民网, 新华网(财经/金融/国际), GitHub Trending, and 微博热搜, then pushes formatted results
  with clickable links to QQ channel. It handles deduplication (same content only
  pushed once per day), date filtering (only today's content), and scheduled execution
  via cron.
name: hot-news
---

# 热点推送 (Hot News)

## 概览

聚合 **6 个来源** 的当日中文热点新闻，自动去重、格式化为可点击链接，按来源分组推送。

适用于：
- 每日定时获取新闻简报
- 实时追踪微博热搜变化
- 关注 GitHub 开源项目趋势

## 运行原理

```
定时触发（cron / 手动调用）
        │
        ▼
 ┌──────────────────────────┐
 │  1. 多源并行采集           │
 │  ├─ 人民网 RSS            │
 │  ├─ 新华网-财经（页面抓取） │
 │  ├─ 新华网-金融（页面抓取） │
 │  ├─ 新华网-国际（页面抓取） │
 │  ├─ GitHub 周榜（REST API）│
 │  └─ 微博热搜（Ajax API）   │
 └────────┬─────────────────┘
          │
          ▼
 ┌──────────────────────────┐
 │  2. 去重过滤               │
 │  ├─ MD5（来源+标题+链接）  │
 │  │   生成 12 位指纹        │
 │  ├─ 与当天已推送记录比对     │
 │  └─ 只保留未推送的新内容     │
 └────────┬─────────────────┘
          │
          ▼
 ┌──────────────────────────┐
 │  3. 格式化输出             │
 │  ├─ 📢 热点汇总 · 日期    │
 │  ├─ 【来源名称】分组标题   │
 │  ├─ N. [标题](链接) 条目   │
 │  └─ ── 共N条 ── 统计尾    │
 └────────┬─────────────────┘
          │
          ▼
 ┌──────────────────────────┐
 │  4. 结果处理               │
 │  ├─ 有新增 → 自动推送      │
 │  ├─ 无新增 → 静默退出      │
 │  └─ 更新 hot_news_sent.json│
 └──────────────────────────┘
```

## 触发方式

| 方式 | 说明 |
|:--|:--|
| **关键词触发** | 说"推送热点""热搜""新闻汇总"等 |
| **手动运行** | 直接执行脚本 |
| **定时任务** | 配置 cron 每 30 分钟自动执行 |

## 文件结构

| 文件 | 说明 |
|:--|:--|
| `scripts/hot_news.py` | 核心采集脚本（~300 行） |
| `memory/hot_news_sent.json` | 已推送记录状态文件（自动维护） |

## 手动运行

```bash
python3 /path/to/workspace/scripts/hot_news.py
```

输出示例：
```
📢 热点汇总 · 2026-06-26

【人民网-今日要闻】
  1. [学习卡丨"人不负青山，青山定不负人"](http://politics.people.com.cn/n1/2025/0605/c1001-40494898.html)
  2. [镜观·足迹｜呵护千山万水 擘画永续发展](http://politics.people.com.cn/n1/2025/0605/c1001-40494899.html)

【微博热搜】
  1. [杨紫听到肖战名字的反应](https://s.weibo.com/weibo?q=杨紫听到肖战名字的反应)

── 共15条 ──
```

## 采集来源详情

| 来源 | 采集方式 | 目标地址 |
|:--|:--|:--|
| 人民网-今日要闻 | RSS 解析 | `http://www.people.com.cn/rss/politics.xml` |
| 新华网-财经优选 | 正则提取 `<a>` 链接 | `http://www.news.cn/fortune/index.htm` |
| 新华网-金融 | 正则提取 `<a>` 链接 | `http://www.news.cn/money/index.html` |
| 新华网-国际要闻 | 正则提取 `<p class="name">` 链接 | `http://www.news.cn/world/index.html` |
| GitHub 周榜 | GitHub REST API `/search/repositories` | `https://api.github.com/search/repositories?q=created:>7days&sort=stars` |
| 微博热搜 | 微博 Ajax API `/side/hotSearch` | `https://weibo.com/ajax/side/hotSearch` |

### 采集策略说明

- **RSS 源**（人民网）：直接解析 XML，稳定可靠
- **页面抓取**（新华网）：因无公开 RSS，通过正则提取首页文章列表。国际频道特殊处理 `<p class="name">` 结构
- **GitHub API**：搜索最近 7 天内创建、按 Star 数降序排列的前 10 个仓库
- **微博 API**：调用微博内部 Ajax 接口，返回实时热搜榜单前 15 条

## 去重机制

```
每条内容 → MD5(source + "|" + title + "|" + link) → 取前 12 位 → 存入 hot_news_sent.json
```

```
hot_news_sent.json 结构：
{
  "2026-06-26": {
    "a1b2c3d4e5f6": true,
    "b2c3d4e5f6a7": true,
    ...
  },
  "2026-06-25": { ... },
  ...  （最多保留 7 天）
}
```

- **同一天**：相同指纹只推送一次
- **跨天**：不同日期的相同内容可以分别推送（新闻具有时效性）
- **自动清理**：超过 7 天的旧记录自动删除

## 定时任务配置

推荐配置（每 30 分钟，北京时间 8:00~21:00 活跃时段）：

```bash
qwenpaw cron create \
  --agent-id default \
  --type agent \
  --schedule-type cron \
  --name "热点推送" \
  --cron "*/30 0-13 * * *" \
  --channel qq \
  --target-user "用户ID" \
  --target-session "会话ID" \
  --text "请运行 python3 scripts/hot_news.py 采集热点新闻，如果有新内容则推送。同一天相同内容只推送一次。" \
  --timeout 120
```

> `*/30 0-13 * * *` 是 UTC 时间，对应北京时间 **8:00~21:30**。
> 非活跃时段（22:00~次日7:00）不执行，避免打扰。

## 自定义配置

脚本开头的配置项可按需修改：

```python
WORK_DIR = "/path/to/workspace"           # 工作区路径
SENT_FILE = "memory/hot_news_sent.json"   # 去重状态文件
UA = "Mozilla/5.0 ..."                    # 请求 User-Agent
```

## 注意事项

1. **容器环境**：如果运行在 Kubernetes 容器中，`WORK_DIR` 需指向持久卷路径，防止重启丢失状态
2. **新华网页面结构**：如果新华网改版，正则匹配可能需要更新
3. **微博 API**：微博内部接口可能随前端更新而变化
4. **推送频率**：建议间隔 ≥ 30 分钟，避免过于频繁
