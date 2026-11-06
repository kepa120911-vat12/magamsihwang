
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from pathlib import Path

st.set_page_config(
    page_title="US MARKET DASHBOARD",
    page_icon="📈",
    layout="wide"
)

BASE = Path(__file__).parent

SYMBOLS = [
    "NVDA","AAPL","MSFT","AMZN","GOOGL","META","AVGO","BRK-B","TSLA","LLY",
    "WMT","JPM","V","ORCL","NFLX","XOM","MA","COST","JNJ","ABBV","PLTR","AMD",
    "BAC","KO","GE","CAT","CSCO","HD","PG","CRM","CVX","IBM","MRK","PM","GS",
    "MS","AXP","UNH","TMO","LIN","MCD","PEP","RTX","INTU","DIS","UBER","NOW",
    "QCOM","TXN","SPCX"
]

KOREAN_NAMES = {
    "NVDA":"엔비디아","AAPL":"애플","MSFT":"마이크로소프트",
    "AMZN":"아마존","GOOGL":"알파벳","META":"메타",
    "AVGO":"브로드컴","BRK-B":"버크셔 해서웨이",
    "TSLA":"테슬라","LLY":"일라이 릴리","WMT":"월마트",
    "JPM":"JP모건","V":"비자","ORCL":"오라클",
    "NFLX":"넷플릭스","XOM":"엑슨모빌","MA":"마스터카드",
    "COST":"코스트코","JNJ":"존슨앤드존슨","ABBV":"애브비",
    "PLTR":"팔란티어","AMD":"AMD","BAC":"뱅크오브아메리카",
    "KO":"코카콜라","GE":"GE 에어로스페이스",
    "CAT":"캐터필러","CSCO":"시스코","HD":"홈디포",
    "PG":"프록터앤드갬블","CRM":"세일즈포스",
    "CVX":"셰브론","IBM":"IBM","MRK":"머크",
    "PM":"필립모리스","GS":"골드만삭스","MS":"모건스탠리",
    "AXP":"아메리칸 익스프레스",
    "UNH":"유나이티드헬스","TMO":"써모 피셔",
    "LIN":"린데","MCD":"맥도날드","PEP":"펩시코",
    "RTX":"RTX","INTU":"인튜이트","DIS":"디즈니",
    "UBER":"우버","NOW":"서비스나우","QCOM":"퀄컴",
    "TXN":"텍사스 인스트루먼트","SPCX":"스페이스X"
}


# ==========================================
# 폰트 자동 조절 함수
# ==========================================

def get_fitted_font(font_path, text, max_size, max_width, max_height):
    size = max_size

    while size > 10:
        font = ImageFont.truetype(str(font_path), size)
        bbox = font.getbbox(text)

        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if width <= max_width and height <= max_height:
            return font

        size -= 2

    return ImageFont.load_default()


# ==========================================
# 주식 데이터 수집
# ==========================================

@st.cache_data(ttl=60)
def get_market_quotes(symbols):

    result = []

    try:
        data = yf.download(
            symbols,
            period="5d",
            group_by="ticker",
            threads=True,
            progress=False
        )

        for ticker in symbols:

            try:
                if len(symbols) == 1:
                    df_ticker = data
                else:
                    if ticker not in data.columns.levels[0]:
                        continue

                    df_ticker = data[ticker]

                df_ticker = df_ticker.dropna(subset=["Close"])

                if df_ticker.empty or len(df_ticker) < 2:
                    continue

                latest = df_ticker.iloc[-1]
                prev = df_ticker.iloc[-2]

                close = float(latest["Close"])
                prev_close = float(prev["Close"])

                change = close - prev_close

                change_pct = (
                    (change / prev_close) * 100
                    if prev_close != 0 else 0.0
                )

                volume = (
                    int(latest["Volume"])
                    if "Volume" in latest and not pd.isna(latest["Volume"])
                    else 0
                )

                t_obj = yf.Ticker(ticker)
                info = getattr(t_obj, "fast_info", None)

                mkt_cap = 0

                if info and hasattr(info, "market_cap"):
                    mkt_cap = info.market_cap

                if not mkt_cap:
                    full_info = t_obj.info
                    mkt_cap = full_info.get("marketCap", 0)

                if not mkt_cap:
                    mkt_cap = 0

                if mkt_cap >= 1e12:
                    mktcap_view = f"{mkt_cap / 1e12:.2f}T"

                elif mkt_cap >= 1e9:
                    mktcap_view = f"{mkt_cap / 1e9:.2f}B"

                else:
                    mktcap_view = f"{mkt_cap:,}"

                result.append({
                    "종목명": KOREAN_NAMES.get(ticker, ticker),
                    "티커": ticker.replace("-", "."),
                    "종가": close,
                    "등락": change,
                    "등락률": change_pct,
                    "시가총액": mktcap_view,
                    "시총숫자": float(mkt_cap),
                    "거래량": f"{volume:,}"
                })

            except Exception:
                continue

    except Exception as e:
        st.error(f"데이터 다운로드 중 오류 발생: {e}")

    return pd.DataFrame(result)


# ==========================================
# 방송용 CG 이미지 생성
# ==========================================

def make_cg_image(rows):

    template_path = BASE / "market_cap_template.jpg"
    font_path = BASE / "RixHead_B.ttf"

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    y_ranges = [
        (310, 423),
        (430, 541),
        (548, 659),
        (666, 777),
        (784, 902)
    ]

    # 기본 폰트 크기
    TICKER_SIZE = 55
    NAME_SIZE = 65
    ARROW_SIZE = 75
    PCT_SIZE = 75

    try:
        font_ticker = ImageFont.truetype(
            str(font_path), TICKER_SIZE
        )

    except Exception:
        font_ticker = ImageFont.load_default()

    # 행별 CG 생성
    for (y1, y2), row in zip(y_ranges, rows[:5]):

        ticker = str(row["티커"])

        # 배경 영역
        draw.rectangle(
            (190, y1, 480, y2),
            fill=(255, 255, 255)
        )

        draw.rectangle(
            (480, y1, 1280, y2),
            fill=(3, 23, 78)
        )

        draw.rectangle(
            (1280, y1, 1730, y2),
            fill=(5, 10, 27)
        )

        draw.line(
            (190, y2, 1730, y2),
            fill=(30, 70, 125),
            width=3
        )

        # --------------------------
        # 종목 로고
        # --------------------------

        logo_candidates = [
            BASE / f"{ticker}.png",
            BASE / f"{ticker.replace('.', '-')}.png",
            BASE / f"{ticker.replace('.', '_')}.png"
        ]

        logo_path = None

        for candidate in logo_candidates:
            if candidate.exists():
                logo_path = candidate
                break

        if logo_path:

            try:
                logo_img = Image.open(logo_path).convert("RGBA")

                box_w = 260
                box_h = 85

                logo_img.thumbnail(
                    (box_w, box_h),
                    Image.Resampling.LANCZOS
                )

                box_center_x = 335
                box_center_y = (y1 + y2) // 2

                logo_x = box_center_x - logo_img.width // 2
                logo_y = box_center_y - logo_img.height // 2

                img.paste(
                    logo_img,
                    (logo_x, logo_y),
                    logo_img
                )

            except Exception:

                b = draw.textbbox(
                    (0, 0), ticker, font=font_ticker
                )

                tw = b[2] - b[0]
                th = b[3] - b[1]

                draw.text(
                    (335 - tw / 2, (y1 + y2 - th) / 2 - b[1]),
                    ticker,
                    font=font_ticker,
                    fill=(20, 20, 20)
                )

        else:

            b = draw.textbbox(
                (0, 0), ticker, font=font_ticker
            )

            tw = b[2] - b[0]
            th = b[3] - b[1]

            draw.text(
                (335 - tw / 2, (y1 + y2 - th) / 2 - b[1]),
                ticker,
                font=font_ticker,
                fill=(20, 20, 20)
            )

        # --------------------------
        # 종목명
        # --------------------------

        name = f'{row["종목명"]}({ticker})'

        font_name = get_fitted_font(
            font_path,
            name,
            NAME_SIZE,
            750,
            (y2 - y1) - 15
        )

        b = draw.textbbox((0, 0), name, font=font_name)

        tw = b[2] - b[0]
        th = b[3] - b[1]

        draw.text(
            (
                880 - tw / 2,
                y1 + (y2 - y1 - th) / 2 - b[1]
            ),
            name,
            font=font_name,
            fill="white"
        )

        # --------------------------
        # 등락률 및 화살표
        # --------------------------

        pct = float(row["등락률"])

        color = (
            (238, 42, 58)
            if pct >= 0
            else (0, 111, 218)
        )

        arrow = "▲" if pct >= 0 else "▼"

        font_arrow = get_fitted_font(
            font_path,
            arrow,
            ARROW_SIZE,
            85,
            (y2 - y1) - 10
        )

        b = draw.textbbox((0, 0), arrow, font=font_arrow)
        th = b[3] - b[1]

        draw.text(
            (
                1300,
                y1 + (y2 - y1 - th) / 2 - b[1]
            ),
            arrow,
            font=font_arrow,
            fill=color
        )

        pct_text = f"{abs(pct):.2f}%"

        font_pct = get_fitted_font(
            font_path,
            pct_text,
            PCT_SIZE,
            300,
            (y2 - y1) - 10
        )

        b = draw.textbbox((0, 0), pct_text, font=font_pct)

        tw = b[2] - b[0]
        th = b[3] - b[1]

        draw.text(
            (
                1710 - tw,
                y1 + (y2 - y1 - th) / 2 - b[1]
            ),
            pct_text,
            font=font_pct,
            fill="white"
        )

    output = BytesIO()

    img.save(output, format="PNG")

    return output.getvalue()


# ==========================================
# 홈페이지 디자인
# ==========================================

st.markdown("""
<style>
.stApp {
    background: #07111f;
    color: #fff;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: #fff;
}
</style>
""", unsafe_allow_html=True)


st.title("🇺🇸 US MARKET DASHBOARD")

st.caption(
    "GLOBAL STOCK MARKET DATA | SOURCE: YAHOO FINANCE"
)

c1, c2 = st.columns([1, 5])

with c1:

    if st.button(
        "🔄 데이터 새로고침",
        use_container_width=True
    ):

        get_market_quotes.clear()
        st.rerun()

with c2:

    now = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).strftime("%Y-%m-%d %H:%M:%S")

    st.caption(f"접속 기준 시각: {now} (KST)")


# ==========================================
# 데이터 출력
# ==========================================

try:

    with st.spinner(
        "야후 파이낸스에서 데이터를 가져오는 중입니다..."
    ):

        df = get_market_quotes(SYMBOLS)

    if df.empty:

        st.error(
            "종목 데이터를 가져오지 못했습니다. "
            "잠시 후 새로고침 버튼을 눌러주세요."
        )

        st.stop()

    df = df[df["시총숫자"] > 0].copy()

    df = (
        df.sort_values("시총숫자", ascending=False)
        .drop_duplicates("티커")
        .reset_index(drop=True)
    )

    df.insert(0, "순위", range(1, len(df) + 1))

    top10 = df.head(10).copy()

    # --------------------------
    # MARKET OVERVIEW
    # --------------------------

    st.subheader("MARKET OVERVIEW")

    st.info(
        "현재 등록된 주요 대형주 후보 종목 내 시가총액 순위입니다."
    )

    st.divider()

    # --------------------------
    # TOP 10
    # --------------------------

    st.subheader("🏆 US MARKET CAP TOP 10")

    st.caption("야후 파이낸스 기준 시가총액 순위")

    display = top10[
        [
            "순위",
            "종목명",
            "티커",
            "종가",
            "등락",
            "등락률",
            "시가총액",
            "거래량"
        ]
    ].copy()

    display["종가"] = display["종가"].map(
        lambda x: f"${x:,.2f}"
    )

    display["등락"] = display["등락"].map(
        lambda x: f"{x:+,.2f}"
    )

    display["등락률"] = display["등락률"].map(
        lambda x: f"{x:+.2f}%"
    )

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True
    )

    st.divider()

    # --------------------------
    # 방송용 CG 이미지
    # --------------------------

    st.subheader("📺 방송용 CG 이미지")

    st.caption(
        "시가총액 1~5위와 6~10위를 각각 1920×1080 PNG로 생성합니다."
    )

    page1 = make_cg_image(
        top10.iloc[:5].to_dict("records")
    )

    page2 = make_cg_image(
        top10.iloc[5:10].to_dict("records")
    )

    a, b = st.columns(2)

    with a:

        st.image(
            page1,
            caption="1장 | 시가총액 1~5위",
            use_container_width=True
        )

        st.download_button(
            "1장 PNG 저장",
            page1,
            "us_market_cap_top10_1-5.png",
            "image/png",
            use_container_width=True
        )

    with b:

        st.image(
            page2,
            caption="2장 | 시가총액 6~10위",
            use_container_width=True
        )

        st.download_button(
            "2장 PNG 저장",
            page2,
            "us_market_cap_top10_6-10.png",
            "image/png",
            use_container_width=True
        )

    st.divider()

    # --------------------------
    # 시가총액 순위 그래프
    # --------------------------

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
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------
    # 전체 수집 종목
    # --------------------------

    with st.expander("전체 수집 종목 확인"):

        st.dataframe(
            df[
                [
                    "순위",
                    "종목명",
                    "티커",
                    "종가",
                    "등락률",
                    "시가총액",
                    "거래량"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

    st.caption(
        f"수집 종목: {len(df)}개 | "
        f"데이터 출처: Yahoo Finance | "
        f"화면 갱신: {now} KST"
    )


except Exception as e:

    st.error(
        f"데이터 수집 또는 CG 생성 중 오류가 발생했습니다: {e}"
    )

    st.info(
        "인터넷 연결 및 CG 템플릿/폰트 파일명을 확인해 주세요."
    )
