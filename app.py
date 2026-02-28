# app.py
# Upgraded mobile-friendly dashboard for AI CapEx Bubble Risk Tracker
# prettier + more practical

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd
import streamlit as st


# =========================================================
# Page Config
# =========================================================
st.set_page_config(
    page_title="AI CapEx Tracker",
    page_icon="📉",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# =========================================================
# Paths
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DAILY_SCORES_FILE = DATA_DIR / "daily_scores.json"
RISK_LOG_FILE = DATA_DIR / "risk_log.json"
ARTICLES_FILE = DATA_DIR / "articles.json"

LEGACY_RISK_LOG_FILE = BASE_DIR / "risk_log.json"
LEGACY_ARTICLES_FILE = BASE_DIR / "articles.json"


# =========================================================
# Labels / Styles
# =========================================================
ITEM_ORDER = [
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

RISK_COLORS = {
    "낮음": {
        "bg": "#E8F5E9",
        "text": "#1B5E20",
        "pill": "#2E7D32",
        "soft": "#F2FBF4",
        "grad1": "#F1FBF4",
        "grad2": "#DDF5E4",
    },
    "보통": {
        "bg": "#ECEFF1",
        "text": "#37474F",
        "pill": "#607D8B",
        "soft": "#F8FAFB",
        "grad1": "#FBFCFD",
        "grad2": "#EDF2F5",
    },
    "주의": {
        "bg": "#FFF3E0",
        "text": "#E65100",
        "pill": "#F57C00",
        "soft": "#FFF8F1",
        "grad1": "#FFF8EF",
        "grad2": "#FFE6C7",
    },
    "경고": {
        "bg": "#FFEBEE",
        "text": "#B71C1C",
        "pill": "#D32F2F",
        "soft": "#FFF5F5",
        "grad1": "#FFF5F6",
        "grad2": "#FFD7DC",
    },
    "위험": {
        "bg": "#F3E5F5",
        "text": "#4A148C",
        "pill": "#7B1FA2",
        "soft": "#FBF5FD",
        "grad1": "#FCF6FE",
        "grad2": "#EED7F6",
    },
}

SCORE_STYLES = {
    0: {"bg": "#F3F4F6", "text": "#6B7280", "pill": "#9CA3AF", "label": "매우 약함", "emoji": "⚪"},
    1: {"bg": "#ECFDF5", "text": "#047857", "pill": "#10B981", "label": "약함", "emoji": "🟢"},
    2: {"bg": "#FFF7ED", "text": "#C2410C", "pill": "#F97316", "label": "중간", "emoji": "🟠"},
    3: {"bg": "#FEF2F2", "text": "#B91C1C", "pill": "#EF4444", "label": "강함", "emoji": "🔴"},
    4: {"bg": "#FDF2F8", "text": "#9D174D", "pill": "#DB2777", "label": "매우 강함", "emoji": "🚨"},
}

TREND_HELP = {
    "낮음": "아직 전반적인 버블 위험 신호는 낮은 편입니다.",
    "보통": "일부 신호가 보이기 시작하는 구간입니다.",
    "주의": "여러 항목에서 의미 있는 경고 신호가 나타나고 있습니다.",
    "경고": "위험 신호가 넓게 확산되는 구간입니다.",
    "위험": "버블 위험을 강하게 시사하는 상태입니다.",
}


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
}

.block-container {
    max-width: 760px;
    padding-top: 1rem;
    padding-bottom: 3.5rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

.main-title {
    font-size: 1.72rem;
    font-weight: 950;
    line-height: 1.15;
    margin-bottom: 0.15rem;
    letter-spacing: -0.03em;
}

.subtle {
    color: #6b7280;
    font-size: 0.92rem;
    line-height: 1.45;
}

.hero-card {
    border-radius: 30px;
    padding: 22px 18px 18px 18px;
    margin: 12px 0 18px 0;
    box-shadow: 0 16px 34px rgba(15, 23, 42, 0.10);
    border: 1px solid rgba(255,255,255,0.65);
    overflow: hidden;
}

.hero-topline {
    font-size: 0.92rem;
    font-weight: 800;
    opacity: 0.88;
}

.hero-score-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 10px;
    margin-top: 8px;
    margin-bottom: 10px;
}

.hero-score {
    font-size: 2.95rem;
    font-weight: 950;
    line-height: 1;
    letter-spacing: -0.04em;
}

.hero-score-unit {
    font-size: 1.02rem;
    font-weight: 800;
    opacity: 0.85;
    margin-left: 4px;
}

.hero-pill {
    display: inline-block;
    padding: 9px 14px;
    border-radius: 999px;
    font-size: 0.9rem;
    font-weight: 900;
    color: white;
    white-space: nowrap;
    box-shadow: 0 6px 14px rgba(0,0,0,0.10);
}

.hero-desc {
    font-size: 0.92rem;
    line-height: 1.5;
    margin-top: 10px;
    opacity: 0.98;
}

.delta-chip {
    display: inline-block;
    margin-top: 10px;
    padding: 7px 11px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 900;
    background: rgba(255,255,255,0.72);
    backdrop-filter: blur(6px);
}

.section-title {
    font-size: 1.08rem;
    font-weight: 900;
    margin-top: 22px;
    margin-bottom: 10px;
    letter-spacing: -0.01em;
}

.kpi-wrap {
    display: flex;
    gap: 10px;
    margin: 10px 0 8px 0;
}

.kpi {
    flex: 1;
    border-radius: 18px;
    padding: 13px 10px;
    text-align: center;
    background: #ffffff;
    border: 1px solid #edf1f5;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}

.kpi-value {
    font-size: 1.22rem;
    font-weight: 900;
    line-height: 1.1;
}

.kpi-label {
    font-size: 0.8rem;
    color: #6b7280;
    margin-top: 4px;
}

.control-card {
    border-radius: 20px;
    padding: 12px 12px 4px 12px;
    background: #ffffff;
    border: 1px solid #edf1f5;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
    margin-bottom: 8px;
}

.item-card {
    border-radius: 22px;
    padding: 14px 14px 13px 14px;
    margin-bottom: 12px;
    border: 1px solid rgba(0,0,0,0.04);
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
}

.item-name {
    font-size: 0.95rem;
    font-weight: 900;
    line-height: 1.3;
}

.item-score {
    font-size: 1.75rem;
    font-weight: 950;
    line-height: 1.05;
    margin-top: 8px;
}

.item-chip {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 850;
    color: white;
    margin-top: 8px;
    margin-bottom: 8px;
}

.item-meta {
    color: #4b5563;
    font-size: 0.84rem;
    line-height: 1.5;
}

.item-count {
    margin-top: 8px;
    font-size: 0.79rem;
    font-weight: 800;
    opacity: 0.85;
}

.evidence-note {
    color: #6b7280;
    font-size: 0.84rem;
    margin-bottom: 8px;
}

.article-card {
    background: #ffffff;
    border: 1px solid #ecf0f4;
    border-radius: 18px;
    padding: 13px 13px;
    margin-bottom: 10px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}

.article-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 8px;
}

.article-title {
    font-size: 0.96rem;
    font-weight: 900;
    line-height: 1.35;
    flex: 1;
}

.article-badge {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 900;
    color: white;
    white-space: nowrap;
}

.article-meta {
    color: #6b7280;
    font-size: 0.8rem;
    line-height: 1.45;
    margin-bottom: 8px;
}

.article-reason {
    font-size: 0.9rem;
    line-height: 1.5;
    color: #111827;
}

.article-signals {
    margin-top: 9px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.signal-chip {
    display: inline-block;
    background: #f3f4f6;
    color: #374151;
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 700;
}

.link-button {
    display: inline-block;
    margin-top: 10px;
    background: #111827;
    color: white !important;
    text-decoration: none;
    padding: 8px 12px;
    border-radius: 12px;
    font-size: 0.82rem;
    font-weight: 800;
}

.footer-note {
    color: #6b7280;
    font-size: 0.82rem;
    line-height: 1.5;
    margin-top: 20px;
}

div[data-testid="stExpander"] details {
    border: 1px solid #edf1f5;
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}

div[data-testid="stExpander"] summary {
    font-weight: 850;
}

@media (max-width: 640px) {
    .hero-score {
        font-size: 2.55rem;
    }

    .block-container {
        padding-left: 0.85rem;
        padding-right: 0.85rem;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# Utils
# =========================================================
def safe_read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_daily_scores() -> List[Dict[str, Any]]:
    rows = safe_read_json(DAILY_SCORES_FILE, [])
    if not isinstance(rows, list):
        rows = []
    rows = sorted(rows, key=lambda x: x.get("date", ""))
    return rows


def load_risk_log() -> List[Dict[str, Any]]:
    rows = safe_read_json(RISK_LOG_FILE, None)
    if rows is None:
        rows = safe_read_json(LEGACY_RISK_LOG_FILE, [])
    if not isinstance(rows, list):
        rows = []
    rows = sorted(rows, key=lambda x: x.get("date", ""))
    return rows


def load_articles_store() -> Dict[str, Any]:
    data = safe_read_json(ARTICLES_FILE, None)
    if data is None:
        data = safe_read_json(LEGACY_ARTICLES_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return data


def fmt_dt(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "-"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def item_label(item_key: str) -> str:
    return ITEM_LABELS.get(item_key, item_key)


def get_risk_style(bucket: str) -> Dict[str, str]:
    return RISK_COLORS.get(bucket, RISK_COLORS["보통"])


def get_score_style(score: int) -> Dict[str, str]:
    score = max(0, min(4, int(score)))
    return SCORE_STYLES[score]


def score_bar(score: int, max_score: int = 4) -> str:
    score = max(0, min(max_score, int(score)))
    return "●" * score + "○" * (max_score - score)


def get_latest_daily_row(daily_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return daily_rows[-1] if daily_rows else None


def get_previous_daily_row(daily_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return daily_rows[-2] if len(daily_rows) >= 2 else None


def get_latest_risk_row(risk_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return risk_rows[-1] if risk_rows else None


def build_trend_df(daily_rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not daily_rows:
        return pd.DataFrame(columns=["date", "overall_score"])

    data = []
    for row in daily_rows:
        data.append({
            "date": row.get("date"),
            "overall_score": row.get("overall_score"),
        })

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df


def get_item_meta_from_daily(latest_daily: Dict[str, Any], item_key: str) -> Dict[str, Any]:
    return ((latest_daily or {}).get("item_meta") or {}).get(item_key, {})


def get_item_evidence_from_risk(latest_risk: Dict[str, Any], item_key: str) -> List[Dict[str, Any]]:
    return ((((latest_risk or {}).get("overall") or {}).get("meta") or {}).get(item_key) or {}).get("evidence", [])


def get_today_overall_score(latest_daily: Optional[Dict[str, Any]], latest_risk: Optional[Dict[str, Any]]) -> float:
    if latest_daily and latest_daily.get("overall_score") is not None:
        return latest_daily.get("overall_score", 0)
    if latest_risk:
        return (((latest_risk.get("overall") or {}).get("score")) or 0)
    return 0


def get_today_risk_level(latest_daily: Optional[Dict[str, Any]], latest_risk: Optional[Dict[str, Any]]) -> str:
    if latest_daily and latest_daily.get("risk_level"):
        return latest_daily.get("risk_level")
    if latest_risk:
        return (((latest_risk.get("overall") or {}).get("bucket")) or "알 수 없음")
    return "알 수 없음"


def get_today_item_scores(latest_daily: Optional[Dict[str, Any]], latest_risk: Optional[Dict[str, Any]]) -> Dict[str, int]:
    if latest_daily and latest_daily.get("item_scores"):
        return latest_daily.get("item_scores", {})
    if latest_risk:
        return (((latest_risk.get("overall") or {}).get("scores")) or {})
    return {k: 0 for k in ITEM_ORDER}


def article_store_to_list(store: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for _, a in store.items():
        if isinstance(a, dict):
            rows.append(a)
    return rows


def build_recent_articles_table(article_store: Dict[str, Any], limit: int = 50) -> pd.DataFrame:
    rows = article_store_to_list(article_store)
    cleaned = []
    for a in rows:
        llm = a.get("llm") or {}
        cleaned.append({
            "item_key": a.get("item", ""),
            "item": item_label(a.get("item", "")),
            "title": a.get("title", ""),
            "published": a.get("published", ""),
            "fetched_at": a.get("fetched_at", ""),
            "relevant": llm.get("relevant"),
            "strength": llm.get("strength"),
            "confidence": llm.get("confidence"),
            "link": a.get("link", ""),
        })

    cleaned = sorted(cleaned, key=lambda x: x.get("published", "") or x.get("fetched_at", ""), reverse=True)[:limit]
    return pd.DataFrame(cleaned)


def make_signal_chips(signals: List[str]) -> str:
    if not signals:
        return ""
    return "".join([f'<span class="signal-chip">{s}</span>' for s in signals])


def evidence_badge(score: int) -> str:
    style = get_score_style(score)
    return f'<span class="article-badge" style="background:{style["pill"]};">{style["label"]}</span>'


def delta_text(current_score: float, prev_score: Optional[float]) -> str:
    if prev_score is None:
        return "이전 비교 데이터 없음"
    delta = round(current_score - prev_score, 1)
    if delta > 0:
        return f"전일 대비 +{delta}"
    if delta < 0:
        return f"전일 대비 {delta}"
    return "전일 대비 변화 없음"


def sorted_item_keys_by_score(item_scores: Dict[str, int]) -> List[str]:
    return sorted(
        ITEM_ORDER,
        key=lambda k: (item_scores.get(k, 0), k),
        reverse=True,
    )


# =========================================================
# Data Load
# =========================================================
daily_rows = load_daily_scores()
risk_rows = load_risk_log()
article_store = load_articles_store()

latest_daily = get_latest_daily_row(daily_rows)
prev_daily = get_previous_daily_row(daily_rows)
latest_risk = get_latest_risk_row(risk_rows)

if latest_daily is None and latest_risk is None:
    st.markdown('<div class="main-title">AI CapEx Bubble Risk Tracker</div>', unsafe_allow_html=True)
    st.warning("표시할 데이터가 아직 없습니다. 먼저 collector.py를 한 번 실행해 주세요.")
    st.stop()

today_score = get_today_overall_score(latest_daily, latest_risk)
today_risk = get_today_risk_level(latest_daily, latest_risk)
today_item_scores = get_today_item_scores(latest_daily, latest_risk)
sorted_items = sorted_item_keys_by_score(today_item_scores)
trend_df = build_trend_df(daily_rows)
risk_style = get_risk_style(today_risk)

prev_score = None if prev_daily is None else prev_daily.get("overall_score")
last_run_at = None
if latest_daily and latest_daily.get("run_at"):
    last_run_at = latest_daily.get("run_at")
elif latest_risk:
    last_run_at = latest_risk.get("date")

article_count_total = (latest_daily or {}).get("article_count_total", len(article_store))
article_count_14d = (latest_daily or {}).get("article_count_14d", 0)
new_articles_today = (latest_daily or {}).get("new_articles_today", 0)

recent_articles_df = build_recent_articles_table(article_store, limit=50)


# =========================================================
# Header
# =========================================================
st.markdown('<div class="main-title">AI CapEx Bubble Risk Tracker</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtle">마지막 업데이트: {fmt_dt(last_run_at) if last_run_at else "-"}</div>',
    unsafe_allow_html=True,
)

# =========================================================
# Hero
# =========================================================
st.markdown(
    f"""
<div class="hero-card" style="background: linear-gradient(135deg, {risk_style["grad1"]} 0%, {risk_style["grad2"]} 100%); color:{risk_style["text"]};">
    <div class="hero-topline">오늘 종합 위험도</div>
    <div class="hero-score-row">
        <div>
            <span class="hero-score">{today_score}</span>
            <span class="hero-score-unit">/ 100</span>
        </div>
        <div class="hero-pill" style="background:{risk_style["pill"]};">{today_risk}</div>
    </div>
    <div class="hero-desc">{TREND_HELP.get(today_risk, "")}</div>
    <div class="delta-chip">{delta_text(today_score, prev_score)}</div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================================================
# KPI
# =========================================================
st.markdown(
    f"""
<div class="kpi-wrap">
    <div class="kpi">
        <div class="kpi-value">{new_articles_today}</div>
        <div class="kpi-label">오늘 신규 기사</div>
    </div>
    <div class="kpi">
        <div class="kpi-value">{article_count_14d}</div>
        <div class="kpi-label">최근 14일 기사</div>
    </div>
    <div class="kpi">
        <div class="kpi-value">{article_count_total}</div>
        <div class="kpi-label">총 저장 기사</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================================================
# Trend
# =========================================================
st.markdown('<div class="section-title">최근 추세</div>', unsafe_allow_html=True)

if trend_df.empty:
    st.info("추세 데이터가 아직 충분하지 않습니다.")
else:
    plot_df = trend_df.copy().set_index("date")
    st.line_chart(plot_df[["overall_score"]], height=230, use_container_width=True)
    if len(plot_df) >= 2:
        last_two = plot_df["overall_score"].tail(2).tolist()
        change = round(last_two[-1] - last_two[-2], 1)
        if change > 0:
            st.caption(f"최근 하루 기준으로 총점이 **{change}점 상승**했습니다.")
        elif change < 0:
            st.caption(f"최근 하루 기준으로 총점이 **{abs(change)}점 하락**했습니다.")
        else:
            st.caption("최근 하루 기준 총점 변화는 없습니다.")

# =========================================================
# Item Cards
# =========================================================
st.markdown('<div class="section-title">항목별 점수</div>', unsafe_allow_html=True)
st.caption("점수가 높은 항목부터 위로 정렬됩니다.")

for idx in range(0, len(sorted_items), 2):
    cols = st.columns(2)
    pair = sorted_items[idx:idx + 2]

    for col, item_key in zip(cols, pair):
        score = int(today_item_scores.get(item_key, 0))
        meta = get_item_meta_from_daily(latest_daily or {}, item_key)
        evidence_count = len(get_item_evidence_from_risk(latest_risk or {}, item_key))
        style = get_score_style(score)

        recent3_count = meta.get("recent3_count", 0)
        recent14_count = meta.get("recent14_count", 0)
        raw_score = meta.get("raw_score", 0)

        with col:
            st.markdown(
                f"""
<div class="item-card" style="background:{style["bg"]}; color:{style["text"]};">
    <div class="item-name">{item_label(item_key)}</div>
    <div class="item-score">{style["emoji"]} {score} / 4</div>
    <div class="item-chip" style="background:{style["pill"]};">{style["label"]}</div>
    <div class="item-meta">
        강도 막대: {score_bar(score)}<br>
        최근 3일: {recent3_count}건<br>
        최근 14일: {recent14_count}건<br>
        raw score: {raw_score}
    </div>
    <div class="item-count">근거 기사 {evidence_count}건</div>
</div>
""",
                unsafe_allow_html=True,
            )

# =========================================================
# Evidence Filters
# =========================================================
st.markdown('<div class="section-title">근거 기사</div>', unsafe_allow_html=True)
st.markdown('<div class="evidence-note">점수 높은 항목부터 표시됩니다.</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="control-card">', unsafe_allow_html=True)
    evidence_min_score = st.selectbox(
        "최소 항목 점수",
        options=[0, 1, 2, 3, 4],
        index=0,
        help="이 점수 이상인 항목만 근거 기사를 보여줍니다.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

for item_key in sorted_items:
    score = int(today_item_scores.get(item_key, 0))
    if score < evidence_min_score:
        continue

    evidence = get_item_evidence_from_risk(latest_risk or {}, item_key)
    score_style = get_score_style(score)

    expander_title = f"{score_style['emoji']} {item_label(item_key)} · {score}/4 · {score_style['label']}"
    with st.expander(expander_title, expanded=False):
        if not evidence:
            st.caption("근거 기사 없음")
            continue

        for ev in evidence:
            title = ev.get("title", "(제목 없음)")
            link = ev.get("link", "")
            published = ev.get("published", "")
            strength = int(ev.get("strength", 0) or 0)
            confidence = int(ev.get("confidence", 0) or 0)
            reason = ev.get("reason", "")
            signals = ev.get("signals", []) or []
            llm_model = ev.get("llm_model", "-")

            title_html = title
            if link:
                title_html = f'<a href="{link}" target="_blank" style="text-decoration:none;color:inherit;">{title}</a>'

            link_button = ""
            if link:
                link_button = f'<a class="link-button" href="{link}" target="_blank">기사 열기</a>'

            st.markdown(
                f"""
<div class="article-card">
    <div class="article-header">
        <div class="article-title">{title_html}</div>
        {evidence_badge(strength)}
    </div>
    <div class="article-meta">
        발행일: {published or "-"}<br>
        strength: {strength} · confidence: {confidence} · model: {llm_model}
    </div>
    <div class="article-reason">{reason or "설명 없음"}</div>
    <div class="article-signals">{make_signal_chips(signals)}</div>
    {link_button}
</div>
""",
                unsafe_allow_html=True,
            )

# =========================================================
# Daily Log
# =========================================================
st.markdown('<div class="section-title">일별 기록</div>', unsafe_allow_html=True)

if daily_rows:
    detail_rows = []
    for row in reversed(daily_rows[-30:]):
        item_scores = row.get("item_scores", {})
        detail_rows.append({
            "날짜": row.get("date"),
            "총점": row.get("overall_score"),
            "위험도": row.get("risk_level"),
            "AI 가격 인하": item_scores.get("ai_price_cuts", 0),
            "경영진 톤 약화": item_scores.get("mgmt_tone_softening", 0),
            "CapEx 증가/매출 둔화": item_scores.get("capex_up_revenue_down", 0),
            "데이터센터 공실": item_scores.get("dc_vacancy", 0),
            "전력/인허가 지연": item_scores.get("power_permit_delays", 0),
            "시장 포지셔닝 과열": item_scores.get("market_positioning", 0),
        })

    df_daily = pd.DataFrame(detail_rows)
    st.dataframe(df_daily, use_container_width=True, hide_index=True)
else:
    st.caption("일별 기록이 아직 없습니다.")

# =========================================================
# Recent Stored Articles
# =========================================================
st.markdown('<div class="section-title">최근 저장 기사</div>', unsafe_allow_html=True)

if recent_articles_df.empty:
    st.caption("저장된 기사가 없습니다.")
else:
    with st.container():
        st.markdown('<div class="control-card">', unsafe_allow_html=True)
        article_item_filter = st.selectbox(
            "항목 필터",
            options=["전체"] + [item_label(k) for k in ITEM_ORDER],
            index=0,
        )
        today_only = st.checkbox("오늘 새 기사만 보기", value=False)
        relevant_only = st.checkbox("관련 기사만 보기", value=False)
        st.markdown("</div>", unsafe_allow_html=True)

    df = recent_articles_df.copy()

    if article_item_filter != "전체":
        reverse_map = {item_label(k): k for k in ITEM_ORDER}
        target_key = reverse_map.get(article_item_filter)
        df = df[df["item_key"] == target_key]

    if today_only:
        if "fetched_at" in df.columns:
            today_prefix = datetime.now().strftime("%Y-%m-%d")
            df = df[df["fetched_at"].astype(str).str.startswith(today_prefix)]

    if relevant_only:
        df = df[df["relevant"] == True]

    df = df.rename(columns={
        "item": "항목",
        "title": "제목",
        "published": "발행일",
        "relevant": "관련여부",
        "strength": "강도",
        "confidence": "신뢰도",
        "link": "링크",
    })

    keep_cols = ["항목", "제목", "발행일", "관련여부", "강도", "신뢰도", "링크"]
    available_cols = [c for c in keep_cols if c in df.columns]
    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.subheader("설정 / 정보")
    st.write(f"Base dir: `{BASE_DIR}`")
    st.write(f"Data dir: `{DATA_DIR}`")
    st.write(f"daily_scores rows: {len(daily_rows)}")
    st.write(f"risk_log rows: {len(risk_rows)}")
    st.write(f"articles stored: {len(article_store)}")

    st.divider()

    show_raw = st.checkbox("최신 raw JSON 보기", value=False)
    if show_raw:
        st.write("latest_daily")
        st.json(latest_daily or {})
        st.write("latest_risk")
        st.json(latest_risk or {})

# =========================================================
# Footer
# =========================================================
st.markdown(
    """
<div class="footer-note">
이 화면은 collector.py가 저장한 결과를 바탕으로 보여준다.<br>
점수는 최근성(fresh bonus)과 14일 decay를 반영한 OVERALL 기준이다.
</div>
""",
    unsafe_allow_html=True,
)