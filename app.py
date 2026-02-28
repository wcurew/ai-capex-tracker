# app.py
# Mobile-friendly dashboard for AI CapEx Bubble Risk Tracker
#
# 실행:
#   streamlit run app.py
#
# collector.py 출력 파일 구조 대응:
#   data/daily_scores.json
#   data/risk_log.json
#   data/articles.json
# fallback:
#   ./risk_log.json
#   ./articles.json

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

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
# Labels / Order / Styles
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

RISK_COLOR = {
    "낮음": "#2E7D32",
    "보통": "#607D8B",
    "주의": "#F57C00",
    "경고": "#D32F2F",
    "위험": "#7B1FA2",
}

SCORE_EMOJI = {
    0: "🟢",
    1: "🟢",
    2: "🟠",
    3: "🔴",
    4: "🚨",
}


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"]  {
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
}

.block-container {
    max-width: 760px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}

.main-title {
    font-size: 1.65rem;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 0.15rem;
}

.subtle {
    color: #6b7280;
    font-size: 0.92rem;
}

.hero-card {
    background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
    border: 1px solid #eceff3;
    border-radius: 22px;
    padding: 20px 18px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    margin: 10px 0 16px 0;
}

.hero-score {
    font-size: 2.5rem;
    font-weight: 900;
    line-height: 1;
    margin-top: 4px;
}

.hero-label {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 0.9rem;
    font-weight: 800;
    color: white;
    margin-top: 10px;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 800;
    margin-top: 20px;
    margin-bottom: 10px;
}

.mini-card {
    background: white;
    border: 1px solid #edf0f4;
    border-radius: 18px;
    padding: 14px 14px 12px 14px;
    margin-bottom: 12px;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.item-name {
    font-size: 0.95rem;
    font-weight: 800;
    line-height: 1.3;
}

.item-score {
    font-size: 1.6rem;
    font-weight: 900;
    margin-top: 6px;
    margin-bottom: 2px;
}

.item-meta {
    color: #6b7280;
    font-size: 0.84rem;
    line-height: 1.4;
}

.article-card {
    background: #fbfcfe;
    border: 1px solid #edf0f4;
    border-radius: 16px;
    padding: 12px 12px;
    margin-bottom: 10px;
}

.article-title {
    font-size: 0.96rem;
    font-weight: 800;
    line-height: 1.35;
    margin-bottom: 5px;
}

.article-meta {
    color: #6b7280;
    font-size: 0.82rem;
    margin-bottom: 6px;
}

.article-reason {
    font-size: 0.9rem;
    line-height: 1.45;
}

.kpi-wrap {
    display: flex;
    gap: 10px;
    margin: 8px 0 8px 0;
}

.kpi {
    flex: 1;
    background: white;
    border: 1px solid #edf0f4;
    border-radius: 16px;
    padding: 12px 12px;
    text-align: center;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.kpi-value {
    font-size: 1.2rem;
    font-weight: 900;
}

.kpi-label {
    font-size: 0.82rem;
    color: #6b7280;
}

.footer-note {
    color: #6b7280;
    font-size: 0.82rem;
    line-height: 1.45;
    margin-top: 20px;
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
    rows = safe_read_json(DAILY_SCORES_FILE, None)
    if rows is None:
        # daily_scores는 legacy가 따로 없으니 없으면 빈 리스트
        rows = []
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


def fmt_date(date_str: Optional[str]) -> str:
    if not date_str:
        return "-"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str


def risk_color(bucket: str) -> str:
    return RISK_COLOR.get(bucket, "#374151")


def item_label(item_key: str) -> str:
    return ITEM_LABELS.get(item_key, item_key)


def score_bar(score: int, max_score: int = 4) -> str:
    score = max(0, min(max_score, int(score)))
    filled = "●" * score
    empty = "○" * (max_score - score)
    return filled + empty


def article_store_to_list(store: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for _, a in store.items():
        if isinstance(a, dict):
            rows.append(a)
    return rows


def get_latest_daily_row(daily_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not daily_rows:
        return None
    return daily_rows[-1]


def get_latest_risk_row(risk_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not risk_rows:
        return None
    return risk_rows[-1]


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


def build_recent_articles_table(article_store: Dict[str, Any], limit: int = 20) -> pd.DataFrame:
    rows = article_store_to_list(article_store)
    cleaned = []
    for a in rows:
        cleaned.append({
            "item": item_label(a.get("item", "")),
            "title": a.get("title", ""),
            "published": a.get("published", ""),
            "link": a.get("link", ""),
            "llm_relevant": ((a.get("llm") or {}).get("relevant")),
            "strength": ((a.get("llm") or {}).get("strength")),
            "confidence": ((a.get("llm") or {}).get("confidence")),
        })

    def sort_key(x):
        return x.get("published", "") or ""

    cleaned = sorted(cleaned, key=sort_key, reverse=True)[:limit]
    return pd.DataFrame(cleaned)


# =========================================================
# Data Load
# =========================================================
daily_rows = load_daily_scores()
risk_rows = load_risk_log()
article_store = load_articles_store()

latest_daily = get_latest_daily_row(daily_rows)
latest_risk = get_latest_risk_row(risk_rows)

today_score = get_today_overall_score(latest_daily, latest_risk)
today_risk = get_today_risk_level(latest_daily, latest_risk)
today_item_scores = get_today_item_scores(latest_daily, latest_risk)

trend_df = build_trend_df(daily_rows)


# =========================================================
# Header
# =========================================================
st.markdown('<div class="main-title">AI CapEx Bubble Risk Tracker</div>', unsafe_allow_html=True)

last_run_at = None
if latest_daily and latest_daily.get("run_at"):
    last_run_at = latest_daily.get("run_at")
elif latest_risk:
    last_run_at = latest_risk.get("date")

st.markdown(
    f'<div class="subtle">마지막 업데이트: {fmt_dt(last_run_at) if last_run_at else "-"}</div>',
    unsafe_allow_html=True,
)

if latest_daily is None and latest_risk is None:
    st.warning("표시할 데이터가 아직 없습니다. 먼저 collector.py를 한 번 실행해 주세요.")
    st.stop()


# =========================================================
# Hero Card
# =========================================================
st.markdown(
    f"""
<div class="hero-card">
    <div class="subtle">오늘 총점</div>
    <div class="hero-score">{today_score} / 100</div>
    <div class="hero-label" style="background:{risk_color(today_risk)};">{today_risk}</div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# KPI Row
# =========================================================
article_count_total = (latest_daily or {}).get("article_count_total", len(article_store))
article_count_14d = (latest_daily or {}).get("article_count_14d", 0)
new_articles_today = (latest_daily or {}).get("new_articles_today", 0)

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
    st.line_chart(plot_df[["overall_score"]], height=220, use_container_width=True)


# =========================================================
# Item Scores
# =========================================================
st.markdown('<div class="section-title">항목별 점수</div>', unsafe_allow_html=True)

for idx in range(0, len(ITEM_ORDER), 2):
    cols = st.columns(2)
    pair = ITEM_ORDER[idx:idx + 2]

    for col, item_key in zip(cols, pair):
        score = int(today_item_scores.get(item_key, 0))
        meta = get_item_meta_from_daily(latest_daily or {}, item_key)

        recent3_count = meta.get("recent3_count", 0)
        recent14_count = meta.get("recent14_count", 0)
        raw_score = meta.get("raw_score", 0)

        with col:
            st.markdown(
                f"""
<div class="mini-card">
    <div class="item-name">{item_label(item_key)}</div>
    <div class="item-score">{SCORE_EMOJI.get(score, "🟢")} {score} / 4</div>
    <div class="item-meta">
        강도 막대: {score_bar(score)}<br>
        최근 3일: {recent3_count}건<br>
        최근 14일: {recent14_count}건<br>
        raw score: {raw_score}
    </div>
</div>
""",
                unsafe_allow_html=True,
            )


# =========================================================
# Evidence
# =========================================================
st.markdown('<div class="section-title">근거 기사</div>', unsafe_allow_html=True)

for item_key in ITEM_ORDER:
    score = int(today_item_scores.get(item_key, 0))
    evidence = get_item_evidence_from_risk(latest_risk or {}, item_key)

    expander_title = f"{item_label(item_key)} · {score}/4"
    with st.expander(expander_title, expanded=False):
        if not evidence:
            st.caption("근거 기사 없음")
            continue

        for ev in evidence:
            title = ev.get("title", "(제목 없음)")
            link = ev.get("link", "")
            published = ev.get("published", "")
            strength = ev.get("strength", 0)
            confidence = ev.get("confidence", 0)
            reason = ev.get("reason", "")
            signals = ev.get("signals", []) or []
            llm_model = ev.get("llm_model", "-")

            title_html = title
            if link:
                title_html = f'<a href="{link}" target="_blank">{title}</a>'

            signals_text = ", ".join(signals) if signals else "-"

            st.markdown(
                f"""
<div class="article-card">
    <div class="article-title">{title_html}</div>
    <div class="article-meta">
        발행일: {published or "-"} · strength: {strength} · confidence: {confidence} · model: {llm_model}
    </div>
    <div class="article-reason">
        {reason or "설명 없음"}
    </div>
    <div class="item-meta" style="margin-top:6px;">
        signals: {signals_text}
    </div>
</div>
""",
                unsafe_allow_html=True,
            )


# =========================================================
# Detailed Trend Table
# =========================================================
st.markdown('<div class="section-title">일별 기록</div>', unsafe_allow_html=True)

if daily_rows:
    detail_rows = []
    for row in reversed(daily_rows[-30:]):
        item_scores = row.get("item_scores", {})
        detail_rows.append({
            "date": row.get("date"),
            "overall_score": row.get("overall_score"),
            "risk_level": row.get("risk_level"),
            "ai_price_cuts": item_scores.get("ai_price_cuts", 0),
            "mgmt_tone_softening": item_scores.get("mgmt_tone_softening", 0),
            "capex_up_revenue_down": item_scores.get("capex_up_revenue_down", 0),
            "dc_vacancy": item_scores.get("dc_vacancy", 0),
            "power_permit_delays": item_scores.get("power_permit_delays", 0),
            "market_positioning": item_scores.get("market_positioning", 0),
        })

    df_daily = pd.DataFrame(detail_rows)
    df_daily = df_daily.rename(columns={
        "date": "날짜",
        "overall_score": "총점",
        "risk_level": "위험도",
        "ai_price_cuts": "AI 가격 인하",
        "mgmt_tone_softening": "경영진 톤 약화",
        "capex_up_revenue_down": "CapEx 증가/매출 둔화",
        "dc_vacancy": "데이터센터 공실",
        "power_permit_delays": "전력/인허가 지연",
        "market_positioning": "시장 포지셔닝 과열",
    })
    st.dataframe(df_daily, use_container_width=True, hide_index=True)
else:
    st.caption("일별 기록이 아직 없습니다.")


# =========================================================
# Recent Articles
# =========================================================
st.markdown('<div class="section-title">최근 저장 기사</div>', unsafe_allow_html=True)

recent_articles_df = build_recent_articles_table(article_store, limit=20)
if recent_articles_df.empty:
    st.caption("저장된 기사가 없습니다.")
else:
    st.dataframe(recent_articles_df, use_container_width=True, hide_index=True)


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
이 화면은 collector.py가 저장한 결과를 읽어서 보여준다.<br>
점수는 최근성(fresh bonus)과 14일 decay를 반영한 운영형 OVERALL 기준이다.
</div>
""",
    unsafe_allow_html=True,
)