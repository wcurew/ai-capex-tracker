# collector.py
# OVERALL only / daily-run decay scoring / prod-ready / mini only
#
# 실행:
#   $env:OPENAI_API_KEY="sk-진짜키"
#   py collector.py

import json
import os
import re
import hashlib
import socket
import time
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta, date, timezone
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser
from dateutil import parser as dtparser

import httpx
from openai import OpenAI


# =========================================================
# Runtime Mode
# =========================================================
RUN_MODE = "prod"   # "fast" or "prod"
FAST_TEST = RUN_MODE == "fast"

# 기존 app.py 호환용 루트 파일도 같이 쓸지
COMPAT_WRITE_LEGACY_FILES = False


# =========================================================
# Paths
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# 운영형 파일
DATA_FILE = DATA_DIR / "risk_log.json"
ART_FILE = DATA_DIR / "articles.json"
DAILY_SCORES_FILE = DATA_DIR / "daily_scores.json"
STATE_FILE = DATA_DIR / "state.json"
RUN_LOG_FILE = DATA_DIR / "run_log.jsonl"
TEXT_LOG_FILE = LOG_DIR / "collector.log"

# 기존 app.py 호환용
LEGACY_DATA_FILE = BASE_DIR / "risk_log.json"
LEGACY_ART_FILE = BASE_DIR / "articles.json"


# =========================================================
# Time
# =========================================================
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def today_kst() -> date:
    return now_kst().date()


def iso_now_kst() -> str:
    return now_kst().isoformat()


# =========================================================
# Network
# =========================================================
socket.setdefaulttimeout(12)

if FAST_TEST:
    OPENAI_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
else:
    OPENAI_TIMEOUT = httpx.Timeout(connect=8.0, read=20.0, write=8.0, pool=8.0)

client = OpenAI(
    http_client=httpx.Client(
        timeout=OPENAI_TIMEOUT,
        trust_env=True,
    )
)


# =========================================================
# Models
# =========================================================
PRIMARY_MODEL = "gpt-5-mini"


# =========================================================
# Config
# =========================================================
ARTICLES_RETENTION_DAYS = 45
MIN_CONFIDENCE = 60
SUMMARY_CHARS = 900
TOP_EVIDENCE = 8

if FAST_TEST:
    MAX_LLM_CALLS_PER_RUN = 8
    MAX_ENTRIES_PER_FEED = 5
    REQUEST_SLEEP_SEC = 0.15
else:
    MAX_LLM_CALLS_PER_RUN = 60
    MAX_ENTRIES_PER_FEED = 50
    REQUEST_SLEEP_SEC = 0.30

ITEM_KEYS = [
    "ai_price_cuts",
    "mgmt_tone_softening",
    "capex_up_revenue_down",
    "dc_vacancy",
    "power_permit_delays",
    "market_positioning",
]

ITEM_LABELS = {
    "ai_price_cuts": "AI 가격 인하",
    "mgmt_tone_softening": "경영진 톤 약화",
    "capex_up_revenue_down": "CapEx 증가 / 매출 둔화",
    "dc_vacancy": "데이터센터 공실/과잉공급",
    "power_permit_delays": "전력/인허가 지연",
    "market_positioning": "시장 포지셔닝 과열",
}

WEIGHTS = {
    "ai_price_cuts": 0.20,
    "mgmt_tone_softening": 0.15,
    "capex_up_revenue_down": 0.20,
    "dc_vacancy": 0.15,
    "power_permit_delays": 0.10,
    "market_positioning": 0.20,
}

if FAST_TEST:
    RSS_BASE_QUERIES = {
        "power_permit_delays": [
            "data center power constraint permitting delay when:14d",
        ],
        "dc_vacancy": [
            "colocation vacancy data center lease concessions when:14d",
        ],
        "ai_price_cuts": [
            "cloud GPU price cut discount credits when:14d",
        ],
        "capex_up_revenue_down": [
            "hyperscaler capex increase cloud growth slowdown when:14d",
        ],
        "mgmt_tone_softening": [
            "earnings call AI capacity lead times easing when:14d",
        ],
        "market_positioning": [
            "investors overinvestment AI capex concerns survey when:14d",
        ],
    }
else:
    RSS_BASE_QUERIES = {
        "power_permit_delays": [
            "data center power constraint permitting delay when:14d",
            "grid interconnection queue data center when:14d",
            "transformer shortage data center delay when:14d",
        ],
        "dc_vacancy": [
            "colocation vacancy data center lease concessions when:14d",
            "data center oversupply vacancy when:14d",
        ],
        "ai_price_cuts": [
            "cloud GPU price cut discount credits when:14d",
            "AI compute price reduction cloud when:14d",
        ],
        "capex_up_revenue_down": [
            "hyperscaler capex increase cloud growth slowdown when:14d",
            "AI capex surge cloud revenue slowdown when:14d",
        ],
        "mgmt_tone_softening": [
            "earnings call AI capacity lead times easing when:14d",
            "AI compute capacity constraint easing earnings when:14d",
        ],
        "market_positioning": [
            "investors overinvestment AI capex concerns survey when:14d",
            "AI capex bubble concerns fund manager survey when:14d",
        ],
    }

STRONG_KEYWORDS = {
    "power_permit_delays": [
        r"\bdelay\b", r"\bbacklog\b", r"\bpermitting\b", r"\binterconnection\b", r"\bqueue\b",
        r"\bpower constraint\b", r"\bgrid\b", r"\btransformer shortage\b"
    ],
    "dc_vacancy": [
        r"\bvacancy\b", r"\boversupply\b", r"\bconcession\b", r"\bincentive\b",
        r"\blease concessions\b", r"\bempty capacity\b", r"\brecord-low vacancy\b"
    ],
    "ai_price_cuts": [
        r"\bprice cut\b", r"\bdiscount\b", r"\bcredit\b", r"\breduce prices\b",
        r"\blower pricing\b", r"\bcheaper\b"
    ],
    "capex_up_revenue_down": [
        r"\bcapex\b", r"\bcapital spending\b", r"\bcloud growth slowdown\b",
        r"\brevenue slowdown\b", r"\bspending surge\b", r"\bcapex risks\b"
    ],
    "mgmt_tone_softening": [
        r"\beasing\b", r"\blead times\b", r"\bcapacity constraint\b",
        r"\bsupply improving\b", r"\bmore available\b"
    ],
    "market_positioning": [
        r"\boverinvestment\b", r"\bbubble\b", r"\bconcerns\b",
        r"\bsurvey\b", r"\bfund manager\b", r"\bpositioning\b"
    ],
}


# =========================================================
# LLM schema
# =========================================================
LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "strength": {"type": "integer", "minimum": 0, "maximum": 4},
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        "reason": {"type": "string"},
        "signals": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["relevant", "strength", "confidence", "reason", "signals"],
    "additionalProperties": False,
}


# =========================================================
# JSON / Logging Utils
# =========================================================
def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_save_json(path, obj):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_json(path, obj):
    atomic_save_json(path, obj)


def append_jsonl(path, row: Dict[str, Any]):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_text_log(message: str):
    ts = now_kst().strftime("%Y-%m-%d %H:%M:%S")
    with open(TEXT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


def sync_legacy_files(risk_log_obj=None, articles_obj=None):
    if not COMPAT_WRITE_LEGACY_FILES:
        return
    if risk_log_obj is not None:
        save_json(LEGACY_DATA_FILE, risk_log_obj)
    if articles_obj is not None:
        save_json(LEGACY_ART_FILE, articles_obj)


# =========================================================
# Text / URL Utils
# =========================================================
def normalize_text(s: str) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_title(title: str) -> str:
    title = normalize_text(title)
    title = re.sub(r"\[[^\]]+\]", " ", title)
    title = re.sub(r"\([^)]+\)", " ", title)
    title = re.sub(r"[^a-z0-9가-힣\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        q = parse_qsl(parsed.query, keep_blank_values=True)
        kept = []
        for k, v in q:
            kl = k.lower()
            if kl.startswith("utm_"):
                continue
            if kl in {"ref", "ref_src", "source", "fbclid", "gclid", "oc", "guccounter"}:
                continue
            kept.append((k, v))
        clean = parsed._replace(
            scheme=(parsed.scheme or "https").lower(),
            netloc=parsed.netloc.lower(),
            query=urlencode(kept, doseq=True),
            fragment=""
        )
        out = urlunparse(clean)
        if out.endswith("/"):
            out = out[:-1]
        return out
    except Exception:
        return url.strip()


def norm_id(title: str, link: str) -> str:
    h = hashlib.sha256((title.strip() + "|" + normalize_url(link)).encode("utf-8")).hexdigest()
    return h[:16]


def dedup_key(title: str, link: str) -> str:
    link_norm = normalize_url(link)
    if link_norm:
        return "L:" + link_norm
    return "T:" + normalize_title(title)


# =========================================================
# Date Utils
# =========================================================
def parse_pub_datetime(published_str: str, fallback_iso: str) -> datetime:
    try:
        if published_str:
            dt = dtparser.parse(published_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(KST)
    except Exception:
        pass

    try:
        dt = datetime.fromisoformat(fallback_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return now_kst()


def parse_pub_date(published_str: str, fallback_iso: str) -> date:
    return parse_pub_datetime(published_str, fallback_iso).date()


def days_old_from_article(a: Dict[str, Any], today: date) -> int:
    pub_date = parse_pub_date(a.get("published", ""), a.get("fetched_at", iso_now_kst()))
    return max(0, (today - pub_date).days)


# =========================================================
# State
# =========================================================
def load_state() -> Dict[str, Any]:
    state = load_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("last_run_at", None)
    state.setdefault("last_overall_score", None)
    return state


def save_state(state: Dict[str, Any]):
    save_json(STATE_FILE, state)


# =========================================================
# Scoring Utils
# =========================================================
def calc_index(scores: Dict[str, int]) -> float:
    total = 0.0
    for k, w in WEIGHTS.items():
        total += (scores.get(k, 0) / 4.0) * w
    return round(total * 100.0, 1)


def risk_bucket(score: float) -> str:
    if score < 20:
        return "낮음"
    if score < 40:
        return "보통"
    if score < 60:
        return "주의"
    if score < 80:
        return "경고"
    return "위험"


def strong_keyword_hit(item_key: str, text: str) -> int:
    pats = STRONG_KEYWORDS.get(item_key, [])
    if not pats:
        return 0
    compiled = [re.compile(p, re.I) for p in pats]
    return 1 if any(p.search(text or "") for p in compiled) else 0


def article_decay_weight(pub_date: date, today: date) -> float:
    days_old = max(0, (today - pub_date).days)
    if days_old > 14:
        return 0.0
    return 0.85 ** days_old


def fresh_bonus_weight(pub_date: date, today: date) -> float:
    days_old = max(0, (today - pub_date).days)
    if days_old == 0:
        return 1.0
    if days_old == 1:
        return 0.8
    if days_old == 2:
        return 0.5
    return 0.0


# =========================================================
# Article Store Helpers
# =========================================================
def load_article_store() -> Dict[str, Any]:
    store = load_json(ART_FILE, None)

    # data/articles.json 없으면 legacy articles.json 읽기
    if store is None and LEGACY_ART_FILE.exists():
        store = load_json(LEGACY_ART_FILE, {})
    if not isinstance(store, dict):
        store = {}
    return store


def save_article_store(store: Dict[str, Any]):
    save_json(ART_FILE, store)
    sync_legacy_files(articles_obj=store)


def prune_articles_store(store: Dict[str, Any], today: date) -> Tuple[Dict[str, Any], int]:
    cutoff = today - timedelta(days=ARTICLES_RETENTION_DAYS)
    kept = {}
    removed = 0
    for aid, a in store.items():
        if not isinstance(a, dict):
            removed += 1
            continue
        pd = parse_pub_date(a.get("published", ""), a.get("fetched_at", iso_now_kst()))
        if pd >= cutoff:
            kept[aid] = a
        else:
            removed += 1
    return kept, removed


def build_existing_dedup_set(store: Dict[str, Any]) -> set:
    seen = set()
    for aid, a in store.items():
        title = a.get("title", "")
        link = a.get("link", "")
        seen.add(dedup_key(title, link))
    return seen


# =========================================================
# LLM classify
# =========================================================
def llm_classify(item_key: str, title: str, summary: str) -> Dict[str, Any]:
    summary = (summary or "")[:SUMMARY_CHARS]

    text_in = (
        f"ITEM_KEY: {item_key}\n"
        f"TITLE: {title}\n"
        f"SUMMARY: {summary}\n\n"
        "Rules:\n"
        "- Be conservative: if only tangential, relevant=false.\n"
        "- strength 0..4 reflects how strong/clear the risk signal is.\n"
        "- Do not infer beyond the text.\n"
        "- Return ONLY JSON.\n"
    )

    retries = 1 if FAST_TEST else 3

    for attempt in range(retries):
        try:
            resp = client.responses.create(
                model=PRIMARY_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": "You are a strict classifier for AI infrastructure and hyperscaler risk signals."
                    },
                    {"role": "user", "content": text_in},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "risk_signal_classification",
                        "schema": LLM_SCHEMA,
                        "strict": True,
                    }
                },
            )
            return json.loads(resp.output_text)

        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.0 * (attempt + 1))


def is_relevant(a: Dict[str, Any]) -> bool:
    llm = a.get("llm")
    if not isinstance(llm, dict):
        return False
    if llm.get("relevant") is not True:
        return False
    try:
        conf = int(llm.get("confidence", 0))
    except Exception:
        conf = 0
    return conf >= MIN_CONFIDENCE


# =========================================================
# RSS
# =========================================================
def google_news_rss_url(query: str, hl: str = "en", gl: str = "US", ceid: str = "US:en") -> str:
    q = query.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"


def build_rss_urls() -> Dict[str, List[str]]:
    urls = {}
    for item_key, qlist in RSS_BASE_QUERIES.items():
        urls[item_key] = [google_news_rss_url(q) for q in qlist]
    return urls


# =========================================================
# Collect + Store
# =========================================================
def fetch_articles_with_llm() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    today = today_kst()

    store = load_article_store()
    store, removed = prune_articles_store(store, today)

    now_iso = iso_now_kst()
    urls = build_rss_urls()

    run_stats = {
        "store_pruned_removed": removed,
        "new_articles": 0,
        "dedup_skips": 0,
        "prefilter_skips": 0,
        "llm_calls": 0,
        "llm_errors": 0,
        "urls_total": 0,
        "urls_ok": 0,
        "urls_fail": 0,
        "per_item_llm_calls": {k: 0 for k in RSS_BASE_QUERIES.keys()},
    }

    seen_dedup = build_existing_dedup_set(store)

    for item_key, url_list in urls.items():
        for url in url_list:
            run_stats["urls_total"] += 1

            try:
                print(f"[OVERALL] FETCH:", url)
                feed = feedparser.parse(url)

                if getattr(feed, "bozo", 0) == 1:
                    run_stats["urls_fail"] += 1
                    print("  !! bozo:", repr(getattr(feed, "bozo_exception", "unknown")))
                    continue

                entries = getattr(feed, "entries", []) or []
                entries = entries[:MAX_ENTRIES_PER_FEED]

                print("  -> entries:", len(entries))
                run_stats["urls_ok"] += 1

            except Exception as ex:
                run_stats["urls_fail"] += 1
                print("  !! fetch failed:", repr(ex))
                continue

            for e in entries:
                title = getattr(e, "title", "") or ""
                link = getattr(e, "link", "") or ""
                published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
                summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""

                if not title and not link:
                    continue

                pub_date = parse_pub_date(published, now_iso)
                if pub_date < (today - timedelta(days=21)):
                    continue

                dk = dedup_key(title, link)
                if dk in seen_dedup:
                    run_stats["dedup_skips"] += 1
                    continue

                aid = norm_id(f"OVERALL|{item_key}|{title}", link)
                if aid in store:
                    run_stats["dedup_skips"] += 1
                    seen_dedup.add(dk)
                    continue

                article_obj = {
                    "id": aid,
                    "group": "OVERALL",
                    "item": item_key,
                    "title": title,
                    "title_norm": normalize_title(title),
                    "link": link,
                    "link_norm": normalize_url(link),
                    "published": published,
                    "summary": summary,
                    "fetched_at": now_iso,
                }

                store[aid] = article_obj
                seen_dedup.add(dk)
                run_stats["new_articles"] += 1

                if run_stats["llm_calls"] >= MAX_LLM_CALLS_PER_RUN:
                    store[aid]["llm_skipped"] = "max_llm_calls_per_run"
                    continue

                if run_stats["per_item_llm_calls"][item_key] >= 2 and FAST_TEST:
                    store[aid]["llm_skipped"] = "max_llm_calls_per_item_per_run"
                    continue

                title_hit = strong_keyword_hit(item_key, title)
                summary_hit = strong_keyword_hit(item_key, summary) if summary else 0
                if title_hit == 0 and summary_hit == 0:
                    store[aid]["llm_skipped"] = "prefilter_no_strong_keywords"
                    run_stats["prefilter_skips"] += 1
                    continue

                print(
                    f"[OVERALL] MINI {run_stats['llm_calls'] + 1}/{MAX_LLM_CALLS_PER_RUN} -> "
                    f"{item_key} | {title[:70]}"
                )

                try:
                    cls = llm_classify(item_key, title, summary)
                    run_stats["llm_calls"] += 1
                    run_stats["per_item_llm_calls"][item_key] += 1
                    store[aid]["llm"] = cls
                    store[aid]["llm_model"] = PRIMARY_MODEL
                    store[aid]["llm_classified_at"] = iso_now_kst()
                except Exception as ex:
                    store[aid]["llm_error"] = str(ex)
                    run_stats["llm_errors"] += 1
                    print("  !! LLM ERROR:", repr(ex))

                time.sleep(REQUEST_SLEEP_SEC)

    save_article_store(store)
    return list(store.values()), run_stats


# =========================================================
# Scoring (OVERALL only)
# =========================================================
def score_item(item_key: str, articles: List[Dict[str, Any]], today: date) -> Tuple[int, Dict[str, Any]]:
    relevant_articles = [
        a for a in articles
        if a.get("group") == "OVERALL" and a.get("item") == item_key and is_relevant(a)
    ]

    recent_14 = []
    recent_3 = []

    for a in relevant_articles:
        pub_date = parse_pub_date(a.get("published", ""), a.get("fetched_at", iso_now_kst()))
        days_old = (today - pub_date).days
        if 0 <= days_old <= 14:
            recent_14.append(a)
        if 0 <= days_old <= 2:
            recent_3.append(a)

    decay_sum = 0.0
    for a in recent_14:
        pub_date = parse_pub_date(a.get("published", ""), a.get("fetched_at", iso_now_kst()))
        w = article_decay_weight(pub_date, today)
        strength = int(a["llm"].get("strength", 0))
        decay_sum += strength * w

    fresh_sum = 0.0
    for a in recent_3:
        pub_date = parse_pub_date(a.get("published", ""), a.get("fetched_at", iso_now_kst()))
        w = fresh_bonus_weight(pub_date, today)
        strength = int(a["llm"].get("strength", 0))
        fresh_sum += strength * w

    strong_hits = sum(strong_keyword_hit(item_key, a.get("title", "")) for a in recent_14)

    raw_score = 0.6 * fresh_sum + 0.4 * decay_sum
    if strong_hits >= 3:
        raw_score += 0.5

    if raw_score < 0.6:
        final_score = 0
    elif raw_score < 1.5:
        final_score = 1
    elif raw_score < 2.5:
        final_score = 2
    elif raw_score < 3.5:
        final_score = 3
    else:
        final_score = 4

    def ev_sort_key(a: Dict[str, Any]):
        stg = int(a["llm"].get("strength", 0))
        conf = int(a["llm"].get("confidence", 0))
        pub_date = parse_pub_date(a.get("published", ""), a.get("fetched_at", iso_now_kst()))
        return (stg, conf, pub_date)

    evidence = [{
        "title": a.get("title", ""),
        "link": a.get("link", ""),
        "published": a.get("published", ""),
        "strength": int(a["llm"].get("strength", 0)),
        "confidence": int(a["llm"].get("confidence", 0)),
        "reason": a["llm"].get("reason", ""),
        "signals": a["llm"].get("signals", []),
        "llm_model": a.get("llm_model", PRIMARY_MODEL),
    } for a in sorted(recent_14, key=ev_sort_key, reverse=True)[:TOP_EVIDENCE]]

    meta = {
        "recent3_count": len(recent_3),
        "recent14_count": len(recent_14),
        "fresh_sum": round(fresh_sum, 2),
        "decay_sum": round(decay_sum, 2),
        "raw_score": round(raw_score, 2),
        "strong_hits14": strong_hits,
        "evidence": evidence,
    }
    return final_score, meta


def score_overall(articles: List[Dict[str, Any]], today: date) -> Tuple[Dict[str, int], Dict[str, Any], float, str]:
    scores = {}
    meta = {}
    for item_key in WEIGHTS.keys():
        s, m = score_item(item_key, articles, today)
        scores[item_key] = s
        meta[item_key] = m

    total = calc_index(scores)
    bucket = risk_bucket(total)
    return scores, meta, total, bucket


# =========================================================
# Daily Snapshots / Logs
# =========================================================
def load_daily_scores() -> List[Dict[str, Any]]:
    rows = load_json(DAILY_SCORES_FILE, [])
    if not isinstance(rows, list):
        rows = []
    return rows


def save_daily_scores(rows: List[Dict[str, Any]]):
    rows = sorted(rows, key=lambda r: r.get("date", ""))
    save_json(DAILY_SCORES_FILE, rows)


def upsert_daily_score(snapshot: Dict[str, Any]):
    rows = load_daily_scores()
    date_str = snapshot["date"]

    replaced = False
    for i, row in enumerate(rows):
        if row.get("date") == date_str:
            rows[i] = snapshot
            replaced = True
            break

    if not replaced:
        rows.append(snapshot)

    save_daily_scores(rows)


def log_run(run_stats: Dict[str, Any], total: float, bucket: str, scores: Dict[str, int]):
    row = {
        "run_at": iso_now_kst(),
        "run_mode": RUN_MODE,
        "primary_model": PRIMARY_MODEL,
        "stats": run_stats,
        "overall_score": total,
        "risk_level": bucket,
        "item_scores": scores,
    }
    append_jsonl(RUN_LOG_FILE, row)

    write_text_log(
        f"mode={RUN_MODE} "
        f"overall={total} "
        f"risk={bucket} "
        f"new_articles={run_stats.get('new_articles', 0)} "
        f"llm_calls={run_stats.get('llm_calls', 0)} "
        f"llm_errors={run_stats.get('llm_errors', 0)}"
    )


# =========================================================
# Main
# =========================================================
def main():
    today = today_kst()
    state = load_state()

    print("=== COLLECT START ===", iso_now_kst(), "| RUN_MODE =", RUN_MODE)

    articles, run_stats = fetch_articles_with_llm()
    scores, meta, total, bucket = score_overall(articles, today)

    out = {
        "date": str(today),
        "overall": {
            "scores": scores,
            "score": total,
            "bucket": bucket,
            "meta": meta,
        },
        "run_stats": run_stats,
    }

    # risk_log.json (기존 app.py 호환)
    log_rows = load_json(DATA_FILE, None)
    if log_rows is None and LEGACY_DATA_FILE.exists():
        log_rows = load_json(LEGACY_DATA_FILE, [])
    if not isinstance(log_rows, list):
        log_rows = []

    log_rows = [r for r in log_rows if r.get("date") != str(today)]
    log_rows.append(out)
    log_rows = sorted(log_rows, key=lambda r: r.get("date", ""))

    save_json(DATA_FILE, log_rows)
    sync_legacy_files(risk_log_obj=log_rows)

    # daily_scores.json (앱 추세 차트용)
    daily_snapshot = {
        "date": str(today),
        "run_at": iso_now_kst(),
        "overall_score": total,
        "risk_level": bucket,
        "item_scores": scores,
        "item_meta": {
            k: {
                "recent3_count": meta[k]["recent3_count"],
                "recent14_count": meta[k]["recent14_count"],
                "fresh_sum": meta[k]["fresh_sum"],
                "decay_sum": meta[k]["decay_sum"],
                "raw_score": meta[k]["raw_score"],
                "strong_hits14": meta[k]["strong_hits14"],
            }
            for k in meta.keys()
        },
        "article_count_total": len(articles),
        "article_count_14d": sum(
            1 for a in articles
            if 0 <= days_old_from_article(a, today) <= 14
        ),
        "new_articles_today": run_stats.get("new_articles", 0),
    }
    upsert_daily_score(daily_snapshot)

    # state
    state["last_run_at"] = iso_now_kst()
    state["last_overall_score"] = total
    state["last_risk_level"] = bucket
    save_state(state)

    # run logs
    log_run(run_stats, total, bucket, scores)

    print("=== DONE ===")
    print("pruned_removed:", run_stats.get("store_pruned_removed"))
    print("new_articles:", run_stats.get("new_articles"))
    print("dedup_skips:", run_stats.get("dedup_skips"), "| prefilter_skips:", run_stats.get("prefilter_skips"))
    print("urls_ok:", run_stats.get("urls_ok"), "| urls_fail:", run_stats.get("urls_fail"))
    print("llm_calls:", run_stats.get("llm_calls"), "| llm_errors:", run_stats.get("llm_errors"))
    print("OVERALL:", total, bucket)
    print("item_scores:", scores)


if __name__ == "__main__":
    main()