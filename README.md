# QwenPaw Agent Skills

QwenPaw 智能体技能合集，提供开箱即用的自动化能力扩展。

## 目录

- [技能列表](#技能列表)
- [快速上手](#快速上手)
- [技能详解](#技能详解)
  - [hot-news：热点新闻采集推送](#hot-news热点新闻采集推送)
- [开发指南](#开发指南)
  - [技能结构规范](#技能结构规范)
  - [安装技能到 QwenPaw](#安装技能到-qwenpaw)

---

## 技能列表

| 技能 | 说明 | 触发关键词 |
|:--|:--|:--|
| [hot-news](skills/hot-news/) | 多来源热点新闻自动采集+去重+推送 | 热点、热搜、新闻推送 |

---

## 快速上手

### 方式一：直接复制到工作区

```bash
git clone https://github.com/gjz518/qwenpaw-skills.git
cp -r qwenpaw-skills/skills/* /path/to/your/workspace/skills/
# QwenPaw 会自动识别并加载新技能
```

### 方式二：通过 `materialize_skill` 安装（需在 QwenPaw 会话中）

```bash
# 在 QwenPaw 工作区中执行
cd /path/to/qwenpaw-skills/skills/hot-news
# 内容通过 QwenPaw 的 materialize_skill 工具注册
```

安装完成后，在 QwenPaw 会话中输入触发关键词即可调用，或配置 cron 定时自动执行。

---

## 技能详解

### hot-news：热点新闻采集推送

聚合 **6 个来源** 的当日热点新闻，自动去重，按来源分组，通过 QQ/其他频道推送可点击的标题链接。

#### 运行原理

```
定时触发 (cron / 手动)
        │
        ▼
 ┌─────────────────────────┐
 │  1. 多源并行采集          │
 │  ├─ 人民网RSS            │
 │  ├─ 新华网×3 (页面抓取)   │
 │  ├─ GitHub周榜 (API)     │
 │  └─ 微博热搜 (API)       │
 └─────────┬───────────────┘
           │
           ▼
 ┌──────────────────────────┐
 │ 2. 去重过滤               │
 │  ├─ MD5(source+title+    │
 │  │     link) 生成指纹     │
 │  ├─ 与当天已推送记录比对    │
 │  └─ 只保留未推送的新内容    │
 └──────────┬───────────────┘
            │
            ▼
 ┌──────────────────────────┐
 │ 3. 格式化输出             │
 │  ├─ 按来源分组            │
 │  ├─ [标题](链接) 可点击格式 │
 │  └─ 只有新内容才推送       │
 └──────────┬───────────────┘
            │
            ▼
 ┌──────────────────────────┐
 │ 4. 多渠道推送             │
 │  ├─ QQ / Discord / 其他  │
 │  └─ 更新已推送状态文件     │
 └──────────────────────────┘
```

#### 采集来源详情

| 来源 | 方式 | 地址 |
|:--|:--|:--|
| 人民网-今日要闻 | RSS | `http://www.people.com.cn/rss/politics.xml` |
| 新华网-财经优选 | 页面抓取 | `http://www.news.cn/fortune/index.htm` |
| 新华网-金融 | 页面抓取 | `http://www.news.cn/money/index.html` |
| 新华网-国际要闻 | 页面抓取 | `http://www.news.cn/world/index.html` |
| GitHub 周榜 | GitHub API | `https://api.github.com/search/repositories` |
| 微博热搜 | 微博 API | `https://weibo.com/ajax/side/hotSearch` |

#### 去重机制

- 每条内容根据 `来源 + 标题 + 链接` 生成 **MD5 指纹（前 12 位）**
- 按日期分桶存储已推送记录，**同一天同一条只推送一次**
- 自动保留最近 **7 天** 的推送记录，过期自动清理
- 不同日期的相同内容允许分别推送（因为新闻具有时效性）

#### 推送格式

```
📢 热点汇总 · 2026-06-26

【人民网-今日要闻】
  1. [标题文字](链接地址)
  2. [标题文字](链接地址)

【微博热搜】
  1. [标题文字](链接地址)
  2. [标题文字](链接地址)

── 共N条 ──
```

每条标题都是可点击的链接，点标题直接跳转原文。

#### 定时任务配置

推荐每 30 分钟运行一次（北京时间 8:00~21:00 活跃时段）：

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

> **注意**：`*/30 0-13 * * *` 是 UTC 时间，对应北京时间 8:00~21:00。

#### 自定义配置

脚本开头的配置项可按需修改：

```python
WORK_DIR = "/path/to/workspace"           # 工作区路径
SENT_FILE = "memory/hot_news_sent.json"   # 去重状态文件
UA = "Mozilla/5.0 ..."                    # 请求 User-Agent
```

---

## 开发指南

### 技能结构规范

每个技能应遵循以下目录结构：

```
skills/<skill-name>/
├── SKILL.md              # 技能描述与使用说明（必需）
└── scripts/              # 辅助脚本（可选）
    └── *.py / *.sh / *.json
```

`SKILL.md` 是技能的入口文件，QwenPaw 通过它了解技能的作用、触发方式和用法。

### 安装技能到 QwenPaw

#### 手动安装

将技能目录复制到工作区的 `skills/` 目录下，QwenPaw 会自动检测并注册：

```bash
cp -r qwenpaw-skills/skills/hot-news /path/to/workspace/skills/
```

#### 通过 materialize_skill 安装

在 QwenPaw 会话中使用内置的 `materialize_skill` 工具注册：

```
materialize_skill(
    name="hot-news",
    description="技能触发描述...",
    body="SKILL.md 内容",
    extra_files={"scripts/hot_news.py": "脚本内容..."}
)
```

#### 验证安装

```bash
ls -la /path/to/workspace/skills/hot-news/
# 应包含 SKILL.md 和 scripts/ 目录
```

安装后可使用 `/技能名` 或关键词触发调用。

---

## 许可

MIT License
