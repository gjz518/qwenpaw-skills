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

## Overview

采集并推送中文热点新闻，来源包括：
- 人民网-今日要闻（通过 RSS）
- 新华网-财经优选 / 金融 / 国际要闻（通过页面抓取）
- GitHub 周榜（通过 GitHub API）
- 微博热搜（通过微博 API）

同一天相同内容只推送一次，按来源分组展示，每条标题可直接点击跳转原文。

## Trigger

用户说以下内容时触发：
- "推送热点"
- "热点汇总"
- "新闻热点"
- "热搜"
- 定时任务自动触发

## 文件结构

| 文件 | 说明 |
|:--|:--|
| `scripts/hot_news.py` | 核心采集脚本 |
| `memory/hot_news_sent.json` | 已推送记录（自动维护） |

## 手动运行

```bash
python3 /run/csi/mount-root/nas/4079184d856ecc166ed19d4887083405/workspaces/default/scripts/hot_news.py
```

输出格式：
```
📢 热点汇总 · 2026-06-26

【来源名称】
  1. [标题](链接)
  2. [标题](链接)

── 共N条 ──
```

## 定时任务

已配置 cron 任务 `热点推送`，每30分钟运行一次（北京时间 8:00~21:00），自动抓取新内容并推送到 QQ。

### 任务参数

- **频率**: `*/30 0-13 * * *` (UTC)
- **类型**: agent
- **频道**: qq
- **会话**: qq:9587D27714BA21F2A87D78B6C2233E0A

### 创建定时任务

```bash
qwenpaw cron create \
  --agent-id default \
  --type agent \
  --schedule-type cron \
  --name "热点推送" \
  --cron "*/30 0-13 * * *" \
  --channel qq \
  --target-user "9587D27714BA21F2A87D78B6C2233E0A" \
  --target-session "qq:9587D27714BA21F2A87D78B6C2233E0A" \
  --text "请运行 python3 scripts/hot_news.py 采集热点新闻，如果有新内容则推送。同一天相同内容只推送一次。" \
  --timeout 120
```

## 采集来源详情

| 来源 | 方式 | API/RSS |
|:--|:--|:--|
| 人民网-今日要闻 | RSS | `http://www.people.com.cn/rss/politics.xml` |
| 新华网-财经优选 | 页面抓取 | `http://www.news.cn/fortune/index.htm` |
| 新华网-金融 | 页面抓取 | `http://www.news.cn/money/index.html` |
| 新华网-国际要闻 | 页面抓取 | `http://www.news.cn/world/index.html` |
| GitHub 周榜 | API | `https://api.github.com/search/repositories` |
| 微博热搜 | API | `https://weibo.com/ajax/side/hotSearch` |

## 去重机制

- 每个条目标题+链接生成 MD5 指纹
- 按日期记录已推送内容，保存 7 天
- 同一天同一条只推送一次
- 跨天不干扰