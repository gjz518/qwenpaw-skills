#!/usr/bin/env python3
"""
热点新闻采集器
每天8:00-21:00每30分钟运行一次
采集来源：人民网、新华网(财经/金融/国际)、GitHub周榜、微博热搜
"""

import json
import os
import re
import ssl
import urllib.request
import urllib.parse
import hashlib
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree

# ===== 配置 =====
BEIJING_TZ = timezone(timedelta(hours=8))
WORK_DIR = "/run/csi/mount-root/nas/4079184d856ecc166ed19d4887083405/workspaces/default"
SENT_FILE = os.path.join(WORK_DIR, "memory/hot_news_sent.json")
UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36"
ctx = ssl.create_default_context()


def now_bj() -> datetime:
    return datetime.now(BEIJING_TZ)


def today_str() -> str:
    return now_bj().strftime("%Y-%m-%d")


def fetch(url, timeout=15, headers=None):
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def collect_people_rss(feed_url, label, limit=8):
    xml = fetch(feed_url)
    if not xml:
        return []
    items = []
    try:
        root = ElementTree.fromstring(xml)
        for entry in root.findall(".//item")[:limit]:
            title = entry.findtext("title", "")
            link = entry.findtext("link", "")
            desc = entry.findtext("description", "")
            desc = re.sub(r"<[^>]+>", "", desc)[:80] if desc else ""
            items.append({
                "source": label,
                "title": title.strip(),
                "link": link.strip(),
                "date": today_str(),
                "desc": desc.strip()
            })
        return items
    except Exception:
        return []


def collect_xinhuanet(category="fortune"):
    paths = {
        "fortune": ("http://www.news.cn/fortune/index.htm", "新华网-财经优选"),
        "finance": ("http://www.news.cn/money/index.html", "新华网-金融"),
        "world":   ("http://www.news.cn/world/index.html", "新华网-国际要闻"),
    }
    url, label = paths.get(category, ("", ""))
    if not url:
        return []
    html = fetch(url)
    if not html:
        return []
    items = []
    try:
        if category == "world":
            for m in re.finditer(
                r'''<p[^>]*\bclass\s*=\s*["']name["'][^>]*>.*?<a[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>''',
                html, re.DOTALL
            ):
                href = m.group(1)
                title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if not title or len(title) < 5:
                    continue
                if not href.startswith("http"):
                    href = ("http://www.news.cn" + href) if href.startswith("/") else "http://www.news.cn/" + href
                items.append({"source": label, "title": title, "link": href, "date": today_str(), "desc": ""})
                if len(items) >= 6:
                    break
        else:
            for m in re.finditer(r'<a[^>]*href="([^"]+\.(?:c\.html|html))"[^>]*>(.*?)</a>', html, re.DOTALL):
                href = m.group(1)
                title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if not title or len(title) < 5:
                    continue
                if not href.startswith("http"):
                    href = "http://www.news.cn" + href
                items.append({"source": label, "title": title, "link": href, "date": today_str(), "desc": ""})
                if len(items) >= 6:
                    break
        return items
    except Exception:
        return []


def collect_github_trending():
    today = now_bj()
    week_ago = today - timedelta(days=7)
    date_str = week_ago.strftime("%Y-%m-%d")
    url = f"https://api.github.com/search/repositories?q=created:>{date_str}&sort=stars&order=desc&per_page=10"
    data = fetch(url, headers={"Accept": "application/vnd.github.v3+json"})
    if not data:
        return []
    try:
        result = json.loads(data)
        items = []
        for repo in result.get("items", [])[:10]:
            items.append({
                "source": "GitHub周榜",
                "title": f"{repo['full_name']} ⭐{repo['stargazers_count']}",
                "link": repo["html_url"],
                "date": today_str(),
                "desc": (repo.get("description") or "")[:80]
            })
        return items
    except Exception:
        return []


def collect_weibo_hot():
    html = fetch("https://weibo.com/ajax/side/hotSearch",
                 headers={"Accept": "application/json,text/plain,*/*",
                          "Referer": "https://weibo.com/"})
    if not html:
        return []
    try:
        data = json.loads(html)
        items = []
        for item in data.get("data", {}).get("realtime", [])[:15]:
            title = item.get("word", "")
            hot = item.get("raw_hot", 0) or item.get("num", 0)
            items.append({
                "source": "微博热搜",
                "title": title,
                "link": f"https://s.weibo.com/weibo?q={urllib.parse.quote(title)}",
                "date": today_str(),
                "desc": f"热度{hot}" if hot else ""
            })
        return items
    except Exception:
        return []


def load_sent():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_sent(sent):
    os.makedirs(os.path.dirname(SENT_FILE), exist_ok=True)
    with open(SENT_FILE, "w") as f:
        json.dump(sent, f, ensure_ascii=False, indent=2)


def is_sent(sent, iid, date):
    return sent.get(date, {}).get(iid, False)


def mark_sent(sent, iid, date):
    if date not in sent:
        sent[date] = {}
    sent[date][iid] = True
    dates = sorted(sent.keys())
    while len(dates) > 7:
        del sent[dates.pop(0)]


def make_item_id(item):
    raw = f"{item['source']}|{item['title']}|{item['link']}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def collect_all():
    all_items = []
    all_items.extend(collect_people_rss("http://www.people.com.cn/rss/politics.xml", "人民网-今日要闻", 8))
    all_items.extend(collect_xinhuanet("fortune"))
    all_items.extend(collect_xinhuanet("finance"))
    all_items.extend(collect_xinhuanet("world"))
    all_items.extend(collect_github_trending())
    all_items.extend(collect_weibo_hot())
    return all_items


def run():
    today = today_str()
    now = now_bj()
    print(f"[{now.strftime('%H:%M:%S')}] 热点采集 - {today}")
    all_items = collect_all()
    print(f"  采集到 {len(all_items)} 条内容")
    sent = load_sent()
    new_items = []
    for item in all_items:
        iid = make_item_id(item)
        if not is_sent(sent, iid, today):
            new_items.append(item)
    print(f"  待推送新内容: {len(new_items)} 条")
    if not new_items:
        print("  \u2713 全部已推送，无需重复发送")
        save_sent(sent)
        return json.dumps({"ok": True, "new_count": 0, "total": len(all_items)})
    grouped = {}
    for item in new_items:
        src = item["source"]
        if src not in grouped:
            grouped[src] = []
        grouped[src].append(item)
    lines = [f"\U0001f4e2 热点汇总 \u00b7 {today}"]
    for src, items in grouped.items():
        lines.append("")
        lines.append(f"\u3010{src}\u3011")
        for i, item in enumerate(items[:5], 1):
            title = item["title"][:60]
            link = item.get("link", "")
            if link:
                lines.append(f"  {i}. [{title}]({link})")
            else:
                lines.append(f"  {i}. {title}")
    lines.append("")
    lines.append(f"\u2500\u2500 \u5171{len(new_items)}\u6761 \u2500\u2500")
    text = "\n".join(lines)
    for item in new_items:
        mark_sent(sent, make_item_id(item), today)
    save_sent(sent)
    print(text)
    return json.dumps({"ok": True, "new_count": len(new_items), "total": len(all_items), "text": text})


if __name__ == "__main__":
    result = run()
    out = os.path.join(WORK_DIR, "memory/last_hot_news.json")
    with open(out, "w") as f:
        f.write(result)
    print(f"\n结果已保存至 {out}")
