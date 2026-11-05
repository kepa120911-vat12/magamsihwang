import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from pathlib import Path

st.set_page_config(page_title="US MARKET DASHBOARD", page_icon="📈", layout="wide")

CNBC_URL = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cnbc.com/"}

# 현재 등록된 후보 종목 50개 기준입니다. 미국 전체 상장기업 전수조사는 아닙니다.
SYMBOLS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "BRK.B", "TSLA",
    "LLY", "WMT", "JPM", "V", "ORCL", "NFLX", "XOM", "MA", "COST", "JNJ",
    "ABBV", "PLTR", "AMD", "BAC", "KO", "GE", "CAT", "CSCO", "HD", "PG",
    "CRM", "CVX", "IBM", "MRK", "PM", "GS", "MS", "AXP", "UNH", "TMO",
    "LIN", "MCD", "PEP", "RTX", "INTU", "DIS", "UBER", "NOW", "QCOM", "TXN"
]

KOREAN_NAMES = {
    "NVDA": "엔비디아", "AAPL": "애플", "MSFT": "마이크로소프트",
    "AMZN": "아마존", "GOOGL": "알파벳", "META": "메타",
    "AVGO": "브로드컴", "BRK.B": "버크셔 해서웨이", "TSLA": "테슬라",
    "LLY": "일라이 릴리", "WMT": "월마트", "JPM": "JP모건",
    "V": "비자", "ORCL": "오라클", "NFLX": "넷플릭스",
    "XOM": "엑슨모빌", "MA": "마스터카드", "COST": "코스트코",
    "JNJ": "존슨앤드존슨", "ABBV": "애브비", "PLTR": "팔란티어",
    "AMD": "AMD", "BAC": "뱅크오브아메리카", "KO": "코카콜라",
    "GE": "GE 에어로스페이스", "CAT": "캐터필러", "CSCO": "시스코",
    "HD": "홈디포", "PG": "프록터앤드갬블", "CRM": "세일즈포스",
    "CVX": "셰브론", "IBM": "IBM", "MRK": "머크", "PM": "필립모리스",
    "GS": "골드만삭스", "MS": "모건스탠리", "AXP": "아메리칸 익스프레스",
    "UNH": "유나이티드헬스", "TMO": "써모 피셔", "LIN": "린데",
    "MCD": "맥도날드", "PEP": "펩시코", "RTX": "RTX",
    "INTU": "인튜이트", "DIS": "디즈니", "UBER": "우버",
    "NOW": "서비스나우", "QCOM": "퀄컴", "TXN": "텍사스 인스트루먼트"
}

@st.cache_data(ttl=60)
def get_cnbc_quotes(symbols):
    params = {
        "symbols": "|".join(symbols), "requestMethod": "itv",
        "noform": "1", "partnerId": "2", "fund": "1",
        "exthrs": "1", "output": "json", "events": "1"
    }
    response = requests.get(CNBC_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    quotes = response.json().get("FormattedQuoteResult", {}).get("FormattedQuote", [])
    if isinstance(quotes, dict):
        quotes = [quotes]
    rows = []
    for item in quotes:
        try:
            symbol = item.get("symbol", "").strip()
            rows.append({
                "종목명": KOREAN_NAMES.get(symbol, item.get("name", symbol)),
                "티커": symbol,
                "종가": float(str(item.get("last", "0")).replace(",", "")),
                "등락": float(str(item.get("change", "0")).replace(",", "")),
                "등락률": float(str(item.get("change_pct", "0")).replace("%", "").replace(",", "").replace("+", "")),
                "시가총액": item.get("mktcapView", ""),
                "거래량": item.get("volume", ""),
            })
        except (ValueError, TypeError):
            continue
    return pd.DataFrame(rows)

def market_cap_to_number(value):
    value = str(value or "").upper().replace(",", "").strip()
    try:
        if value.endswith("T"): return float(value[:-1]) * 1_000_000_000_000
        if value.endswith("B"): return float(value[:-1]) * 1_000_000_000
        if value.endswith("M"): return float(value[:-1]) * 1_000_000
        return float(value)
    except ValueError:
        return 0

def make_cg_image(rows, page_number):
    """기존 1920x1080 CG 배경을 유지하고 5개 행의 종목/등락률만 교체합니다."""
    template_path = Path(__file__).with_name("market_cap_template.jpg")
    font_path = Path(__file__).with_name("NanumGothic.ttf")
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_name = ImageFont.truetype(str(font_path), 43)
    font_ticker = ImageFont.truetype(str(font_path), 30)
    font_pct = ImageFont.truetype(str(font_path), 66)
    font_arrow = ImageFont.truetype(str(font_path), 72)

    # 템플릿의 5개 행 좌표(1920x1080 원본 기준)
    row_tops = [266, 369, 472, 575, 678]
    row_bottoms = [363, 466, 569, 672, 775]

    for i, row in enumerate(rows[:5]):
        y1, y2 = row_tops[i], row_bottoms[i]
        pct = float(row["등락률"])
        up = pct >= 0

        # 로고 칸은 티커 표기로 바꾸고, 가운데 종목명/티커를 최신 순위에 맞춰 교체
        draw.rectangle((165, y1 + 2, 411, y2 - 2), fill=(255, 255, 255))
        draw.rectangle((414, y1 + 2, 1098, y2 - 2), fill=(3, 22, 73))
        draw.rectangle((1103, y1 + 2, 1484, y2 - 2), fill=(7, 10, 28))

        ticker = str(row["티커"])
        company = str(row["종목명"])
        ticker_font = font_ticker
        ticker_box = draw.textbbox((0, 0), ticker, font=ticker_font)
        ticker_w = ticker_box[2] - ticker_box[0]
        draw.text((288 - ticker_w / 2, y1 + 28), ticker, font=ticker_font, fill=(20, 20, 20))

        name_text = f"{company}({ticker})"
        # 긴 종목명은 작은 글꼴로 줄여 칸 안에 맞춥니다.
        name_font = font_name
        while draw.textbbox((0, 0), name_text, font=name_font)[2] > 650 and name_font.size > 27:
            name_font = ImageFont.truetype(str(font_path), name_font.size - 2)
        box = draw.textbbox((0, 0), name_text, font=name_font)
        text_w, text_h = box[2] - box[0], box[3] - box[1]
        draw.text((756 - text_w / 2, y1 + (97 - text_h) / 2 - 4), name_text, font=name_font, fill="white")

        color = (239, 43, 58) if up else (0, 113, 218)
        arrow = "▲" if up else "▼"
        draw.text((1150, y1 + 7), arrow, font=font_arrow, fill=color)
        pct_text = f"{abs(pct):.2f}%"
        pct_box = draw.textbbox((0, 0), pct_text, font=font_pct)
        pct_w = pct_box[2] - pct_box[0]
        draw.text((1455 - pct_w, y1 + 10), pct_text, font=font_pct, fill="white")

    # 1장/2장 제목 구분
    title = f"미국 시총상위 TOP10  ({'1~5위' if page_number == 1 else '6~10위'})"
    title_font = ImageFont.truetype(str(font_path), 1)  # 기존 제목은 배경에 포함되어 있어 덧씌우지 않습니다.
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()

st.markdown("""
<style>
.stApp {background-color:#07111f;color:#fff}
.block-container {padding-top:2rem;padding-bottom:2rem}
h1,h2,h3 {color:#fff}
div[data-testid="stMetric"] {background:#111f32;padding:18px;border-radius:10px;border:1px solid #26364b}
</style>
""", unsafe_allow_html=True)

st.title("🇺🇸 US MARKET DASHBOARD")
st.caption("GLOBAL STOCK MARKET DATA | SOURCE: CNBC")
c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        get_cnbc_quotes.clear()
        st.rerun()
with c2:
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"접속 기준 시각: {now} (KST)")

try:
    with st.spinner("CNBC에서 데이터를 가져오는 중입니다..."):
        df = get_cnbc_quotes(SYMBOLS)
    if df.empty:
        st.error("CNBC에서 종목 데이터를 가져오지 못했습니다.")
        st.stop()

    df["시총숫자"] = df["시가총액"].apply(market_cap_to_number)
    df = df[df["시총숫자"] > 0].copy()
    df = df.sort_values("시총숫자", ascending=False).drop_duplicates("티커").reset_index(drop=True)
    df.insert(0, "순위", range(1, len(df) + 1))
    top10 = df.head(10).copy()

    st.subheader("MARKET OVERVIEW")
    st.info("현재 등록된 주요 대형주 후보 종목 내 시가총액 순위입니다. 미국 전체 상장기업 전수 순위는 아닙니다.")

    st.divider()
    st.subheader("🏆 US MARKET CAP TOP 10")
    st.caption("CNBC 제공 시가총액 기준 | 등록 후보 종목 내 순위")
    display_df = top10[["순위", "종목명", "티커", "종가", "등락", "등락률", "시가총액", "거래량"]].copy()
    display_df["종가"] = display_df["종가"].map(lambda x: f"${x:,.2f}")
    display_df["등락"] = display_df["등락"].map(lambda x: f"{x:+,.2f}")
    display_df["등락률"] = display_df["등락률"].map(lambda x: f"{x:+.2f}%")
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("📺 방송용 CG 이미지")
    st.caption("현재 시가총액 순위 1~5위와 6~10위를 각각 PNG로 만듭니다.")
    page1 = make_cg_image(top10.iloc[:5].to_dict("records"), 1)
    page2 = make_cg_image(top10.iloc[5:10].to_dict("records"), 2)
    cg1, cg2 = st.columns(2)
    with cg1:
        st.image(page1, caption="1장 | 시가총액 1~5위", use_container_width=True)
        st.download_button("1장 PNG 저장", page1, "us_market_cap_top10_1-5.png", "image/png", use_container_width=True)
    with cg2:
        st.image(page2, caption="2장 | 시가총액 6~10위", use_container_width=True)
        st.download_button("2장 PNG 저장", page2, "us_market_cap_top10_6-10.png", "image/png", use_container_width=True)

    st.divider()
    st.subheader("MARKET CAP RANKING")
    chart_df = top10.sort_values("시총숫자", ascending=True)
    fig = px.bar(chart_df, x="시총숫자", y="티커", orientation="h", text="시가총액",
                 template="plotly_dark", labels={"시총숫자":"Market Cap (USD)", "티커":"Ticker"})
    fig.update_layout(paper_bgcolor="#07111f", plot_bgcolor="#07111f", font_color="white",
                      height=450, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("전체 수집 종목 확인"):
        st.dataframe(df[["순위", "종목명", "티커", "종가", "등락률", "시가총액", "거래량"]],
                     hide_index=True, use_container_width=True)
    st.caption(f"수집 종목: {len(df)}개 | 데이터 출처: CNBC | 화면 갱신: {now} KST")
except Exception as e:
    st.error(f"데이터 수집 또는 CG 생성 중 오류가 발생했습니다: {e}")
    st.info("인터넷 연결, CNBC 데이터 응답, CG 템플릿/폰트 파일을 확인해 주세요.")
