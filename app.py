
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# 기본 설정
# ==========================================

st.set_page_config(
    page_title="US MARKET DASHBOARD",
    page_icon="📈",
    layout="wide"
)

CNBC_URL = (
    "https://quote.cnbc.com/quote-html-webservice/"
    "restQuote/symbolType/symbol"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.cnbc.com/"
}

# 우선 미국 주요 대형주 후보군
SYMBOLS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", 
    "SPCX", "META", "AVGO", "BRK.B", "TSLA",
    "LLY", "WMT", "JPM", "V", "ORCL",
    "NFLX", "XOM", "MA", "COST", "JNJ",
    "ABBV", "PLTR", "AMD", "BAC", "KO",
    "GE", "CAT", "CSCO", "HD", "PG",
    "CRM", "CVX", "IBM", "MRK", "PM",
    "GS", "MS", "AXP", "UNH", "TMO",
    "LIN", "MCD", "PEP", "RTX", "INTU",
    "DIS", "UBER", "NOW", "QCOM", "TXN"
]

# ==========================================
# 디자인
# ==========================================

st.markdown("""
<style>
.stApp {
    background-color: #07111f;
    color: #ffffff;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: #ffffff;
}

.metric-card {
    background: #111f32;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #26364b;
}

div[data-testid="stMetric"] {
    background: #111f32;
    padding: 18px;
    border-radius: 10px;
    border: 1px solid #26364b;
}

div[data-testid="stMetricLabel"] {
    color: #9fb1c8;
}

div[data-testid="stMetricValue"] {
    color: white;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# CNBC 데이터 수집
# ==========================================

@st.cache_data(ttl=60)
def get_cnbc_quotes(symbols):

    params = {
        "symbols": "|".join(symbols),
        "requestMethod": "itv",
        "noform": "1",
        "partnerId": "2",
        "fund": "1",
        "exthrs": "1",
        "output": "json",
        "events": "1"
    }

    response = requests.get(
        CNBC_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    quotes = result.get(
        "FormattedQuoteResult", {}
    ).get("FormattedQuote", [])

    if isinstance(quotes, dict):
        quotes = [quotes]

    rows = []

    for item in quotes:

        try:
            rows.append({
                "종목명": item.get("name", ""),
                "티커": item.get("symbol", ""),
               "종가": float(
                item.get("last", "0").replace(",", "")
                ),
                "등락": float(
                    item.get("change", "0").replace(",", "")
                ),
                "등락률": float(
                    item.get("change_pct", "0")
                    .replace("%", "")
                    .replace(",", "")
                    .replace("+", "")
                ),
                "시가총액": item.get("mktcapView", ""),
                "거래량": item.get("volume", ""),
                "거래소": item.get("exchange", ""),
                "기준시각": item.get("last_time", "")
            })

        except (ValueError, TypeError):
            continue

    return pd.DataFrame(rows)


def market_cap_to_number(value):

    if not value:
        return 0

    value = str(value).upper().replace(",", "").strip()

    try:
        if value.endswith("T"):
            return float(value[:-1]) * 1_000_000_000_000

        if value.endswith("B"):
            return float(value[:-1]) * 1_000_000_000

        if value.endswith("M"):
            return float(value[:-1]) * 1_000_000

        return float(value)

    except ValueError:
        return 0


# ==========================================
# 상단 헤더
# ==========================================

st.title("🇺🇸 US MARKET DASHBOARD")

st.caption(
    "GLOBAL STOCK MARKET DATA | SOURCE: CNBC"
)

st.divider()

# ==========================================
# 업데이트
# ==========================================

col1, col2 = st.columns([1, 5])

with col1:
    if st.button("🔄 데이터 새로고침", width="stretch"):
        get_cnbc_quotes.clear()
        st.rerun()

with col2:
    now = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).strftime("%Y-%m-%d %H:%M:%S")

    st.caption(f"접속 기준 시각: {now} (KST)")

# ==========================================
# 데이터 로딩
# ==========================================

try:

    with st.spinner("CNBC에서 데이터를 가져오는 중입니다..."):

        df = get_cnbc_quotes(SYMBOLS)

    if df.empty:
        st.error("CNBC에서 종목 데이터를 가져오지 못했습니다.")
        st.stop()

    df["시총숫자"] = df["시가총액"].apply(
        market_cap_to_number
    )

    df = df[df["시총숫자"] > 0].copy()

    df = df.sort_values(
        "시총숫자",
        ascending=False
    ).reset_index(drop=True)

    df.insert(0, "순위", range(1, len(df) + 1))

    top10 = df.head(10).copy()

    # ======================================
    # 주요 시장 지표
    # ======================================

    st.subheader("MARKET OVERVIEW")

    # 지수 데이터는 다음 단계에서 CNBC 지수 심볼을 확인해 연결
    st.info(
        "주요 지수 데이터는 종목 데이터 연결 확인 후 추가할 예정입니다."
    )

    # ======================================
    # TOP 10
    # ======================================

    st.divider()

    st.subheader("🏆 US MARKET CAP TOP 10")

    st.caption(
        "CNBC 제공 시가총액 기준 | 주요 대형주 후보군 내 순위"
    )

    display_df = top10[
        ["순위", "종목명", "티커", "종가",
         "등락", "등락률", "시가총액", "거래량"]
    ].copy()

    display_df["종가"] = display_df["종가"].map(
        lambda x: f"${x:,.2f}"
    )

    display_df["등락"] = display_df["등락"].map(
        lambda x: f"{x:+,.2f}"
    )

    display_df["등락률"] = display_df["등락률"].map(
        lambda x: f"{x:+.2f}%"
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch"
    )

    # ======================================
    # 시가총액 차트
    # ======================================

    st.divider()

    st.subheader("MARKET CAP RANKING")

    chart_df = top10.sort_values(
        "시총숫자",
        ascending=True
    )

    fig = px.bar(
        chart_df,
        x="시총숫자",
        y="티커",
        orientation="h",
        text="시가총액",
        template="plotly_dark",
        labels={
            "시총숫자": "Market Cap (USD)",
            "티커": "Ticker"
        }
    )

    fig.update_layout(
        paper_bgcolor="#07111f",
        plot_bgcolor="#07111f",
        font_color="white",
        height=450,
        margin=dict(l=20, r=20, t=30, b=20)
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    # ======================================
    # 전체 후보 종목
    # ======================================

    with st.expander("전체 수집 종목 확인"):

        st.dataframe(
            df[
                ["순위", "종목명", "티커", "종가",
                 "등락률", "시가총액", "거래량"]
            ],
            hide_index=True,
            width="stretch"
        )

    st.caption(
        f"수집 종목: {len(df)}개 | "
        f"데이터 출처: CNBC | "
        f"화면 갱신: {now} KST"
    )

except Exception as e:

    st.error(f"데이터 수집 중 오류가 발생했습니다: {e}")

    st.info(
        "인터넷 연결이나 CNBC 데이터 응답을 확인해 주세요."
    )

