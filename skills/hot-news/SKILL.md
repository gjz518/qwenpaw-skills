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

## 运行原理

```
每日晚8点定时触发（或手动调用）
        │
        ▼
 ┌──────────────────────────┐
 │  1. 多源并行采集           │
 │  ├─ 人民网 RSS            │
 │  ├─ 新华网-财经（页面抓取）│
 │  ├─ 新华网-金融（页面抓取）│
 │  ├─ 新华网-国际（页面抓取）│
 │  ├─ GitHub 周榜（REST API）│
 │  └─ 微博热搜（Ajax API）   │
 └────────┬─────────────────┘
          │
          ▼
 ┌──────────────────────────┐
 │  2. 按来源分组             │
 │  └─ 每组取前5条            │
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
 │  4. 推送或展示             │
 │  ├─ 定时任务 → 自动推QQ   │
 │  └─ 手动运行 → 仅展示结果  │
 └──────────────────────────┘
```

## 触发方式

| 方式 | 说明 |
|:--|:--|
| **关键词触发** | 说"推送热点""热搜""新闻汇总"等 |
| **手动运行** | 执行 `python3 scripts/hot_news.py` |
| **定时任务** | 每晚 20:00（北京时间）自动推送 |

## 文件结构

| 文件 | 说明 |
|:--|:--|
| `scripts/hot_news.py` | 核心采集脚本 |
| `memory/hot_news_sent.json` | 已推送记录（自动维护） |

## 手动运行

```bash
# 普通模式：只显示未推送的新内容
python3 scripts/hot_news.py

# 每日汇总模式：清除今日记录，生成完整汇总
python3 scripts/hot_news.py --daily
```

输出示例：
```
📢 热点汇总 · 2026-06-28

【人民网-今日要闻】
  1. [学习卡丨"人不负青山，青山定不负人"](http://politics.people.com.cn/n1/2025/0605/c1001-40494898.html)
  2. [镜观·足迹｜呵护千山万水 擘画永续发展](http://politics.people.com.cn/n1/2025/0605/c1001-40494899.html)

── 共51条 ──
```

## 定时任务

每晚 20:00（北京时间）推送一次全天完整汇总，使用 `--daily` 模式确保包含当日所有内容。

### 任务参数

- **频率**: `0 12 * * *` (UTC，北京时间 20:00)
- **命令**: `python3 scripts/hot_news.py --daily`
- **频道**: qq
- **类型**: agent

### 创建定时任务

```bash
qwenpaw cron create \
  --agent-id default \
  --type agent \
  --schedule-type cron \
  --name "热点推送" \
  --cron "0 12 * * *" \
  --channel qq \
  --target-user "用户ID" \
  --target-session "会话ID" \
  --text "请运行 python3 scripts/hot_news.py --daily 采集热点新闻并推送全天完整汇总。" \
  --timeout 120
```

## 采集来源详情

| 来源 | 采集方式 | 目标地址 |
|:--|:--|:--|
| 人民网-今日要闻 | RSS 解析 | `http://www.people.com.cn/rss/politics.xml` |
| 新华网-财经优选 | 正则提取 `<a>` 链接 | `http://www.news.cn/fortune/index.htm` |
| 新华网-金融 | 正则提取 `<a>` 链接 | `http://www.news.cn/money/index.html` |
| 新华网-国际要闻 | 正则提取 `<p class="name">` | `http://www.news.cn/world/index.html` |
| GitHub 周榜 | GitHub REST API | `https://api.github.com/search/repositories` |
| 微博热搜 | 微博 Ajax API | `https://weibo.com/ajax/side/hotSearch` |

## 去重机制

```
每条内容 → MD5(source + "|" + title + "|" + link) → 取前12位 → 存入 hot_news_sent.json
```

- 同一天相同指纹只推送一次
- 自动清理 7 天前的旧记录
- `--daily` 模式会清除今日状态，强制重新生成完整汇总

## 注意事项

1. **脚本路径**：确保 `WORK_DIR` 指向正确的 QwenPaw 工作区路径
2. **容器环境**：如运行在 Kubernetes 中，需指向持久卷路径
3. **手动运行不推送**：仅在对话中展示结果，不会主动推送到频道
