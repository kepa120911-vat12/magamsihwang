import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from pathlib import Path


# ==========================================
# 기본 설정
# ==========================================

st.set_page_config(
    page_title="US MARKET DASHBOARD",
    page_icon="📈",
    layout="wide"
)

BASE = Path(__file__).parent

TEMPLATE_PATH = BASE / "market_cap_template.jpg"
FONT_PATH = BASE / "RIXHEADB.TTF"

# 필라델피아 반도체 방송용 CG 원본 이미지
SOX_TEMPLATE_1 = BASE / "필반 1장.png"
SOX_TEMPLATE_2 = BASE / "필반 2장.png"


# ==========================================
# 시가총액 TOP10 후보 종목
# ==========================================

SYMBOLS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META",
    "AVGO", "BRK-B", "TSLA", "LLY", "WMT", "JPM",
    "V", "ORCL", "NFLX", "XOM", "MA", "COST",
    "JNJ", "ABBV", "PLTR", "AMD", "BAC", "KO",
    "GE", "CAT", "CSCO", "HD", "PG", "CRM",
    "CVX", "IBM", "MRK", "PM", "GS", "MS",
    "AXP", "UNH", "TMO", "LIN", "MCD", "PEP",
    "RTX", "INTU", "DIS", "UBER", "NOW", "QCOM",
    "TXN", "SPCX"
]


# ==========================================
# 반도체 고정 구성종목 10개
# ==========================================

SOX_SYMBOLS = [
    "NVDA", "AVGO", "MU", "INTC", "MRVL",
    "AMD", "TXN", "QCOM", "KLAC", "LRCX"
]

# 업로드한 필반 CG 이미지에 인쇄된 종목 순서와 일치시킵니다.
SOX_PAGE1_ORDER = ["NVDA", "AVGO", "MU", "AMD", "INTC"]
SOX_PAGE2_ORDER = ["TXN", "LRCX", "KLAC", "QCOM", "MRVL"]


# ==========================================
# 종목 한글명
# ==========================================

KOREAN_NAMES = {
    "NVDA": "엔비디아",
    "AAPL": "애플",
    "MSFT": "마이크로소프트",
    "AMZN": "아마존",
    "GOOGL": "알파벳",
    "META": "메타",
    "AVGO": "브로드컴",
    "BRK-B": "버크셔 해서웨이",
    "TSLA": "테슬라",
    "LLY": "일라이 릴리",
    "WMT": "월마트",
    "JPM": "JP모건",
    "V": "비자",
    "ORCL": "오라클",
    "NFLX": "넷플릭스",
    "XOM": "엑슨모빌",
    "MA": "마스터카드",
    "COST": "코스트코",
    "JNJ": "존슨앤드존슨",
    "ABBV": "애브비",
    "PLTR": "팔란티어",
    "AMD": "AMD",
    "BAC": "뱅크오브아메리카",
    "KO": "코카콜라",
    "GE": "GE 에어로스페이스",
    "CAT": "캐터필러",
    "CSCO": "시스코",
    "HD": "홈디포",
    "PG": "프록터앤드갬블",
    "CRM": "세일즈포스",
    "CVX": "셰브론",
    "IBM": "IBM",
    "MRK": "머크",
    "PM": "필립모리스",
    "GS": "골드만삭스",
    "MS": "모건스탠리",
    "AXP": "아메리칸 익스프레스",
    "UNH": "유나이티드헬스",
    "TMO": "써모 피셔",
    "LIN": "린데",
    "MCD": "맥도날드",
    "PEP": "펩시코",
    "RTX": "RTX",
    "INTU": "인튜이트",
    "DIS": "디즈니",
    "UBER": "우버",
    "NOW": "서비스나우",
    "QCOM": "퀄컴",
    "TXN": "텍사스 인스트루먼트",
    "SPCX": "스페이스X",

    # 반도체 추가 종목
    "MU": "마이크론",
    "INTC": "인텔",
    "MRVL": "마벨",
    "KLAC": "KLA",
    "LRCX": "램리서치"
}


# ==========================================
# 공통 데이터 추출 함수
# ==========================================

def get_ticker_data(data, ticker):

    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):

        level0 = data.columns.get_level_values(0)
        level1 = data.columns.get_level_values(1)

        if ticker in level0:
            return data[ticker]

        if ticker in level1:
            return data.xs(ticker, axis=1, level=1)

        return pd.DataFrame()

    return data


# ==========================================
# 시가총액 표시 함수
# ==========================================

def format_market_cap(value):

    if not value:
        return "-"

    if value >= 1e12:
        return f"{value / 1e12:.2f}T"

    elif value >= 1e9:
        return f"{value / 1e9:.2f}B"

    elif value >= 1e6:
        return f"{value / 1e6:.2f}M"

    return f"{value:,.0f}"


# ==========================================
# 주식 데이터 수집
# ==========================================

@st.cache_data(ttl=60)
def get_market_quotes(symbols):

    result = []

    now_et = datetime.now(
        ZoneInfo("America/New_York")
    )

    today_et = now_et.date()

    try:

        daily_data = yf.download(
            symbols,
            period="5d",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=False
        )

        intraday_data = yf.download(
            symbols,
            period="1d",
            interval="1m",
            group_by="ticker",
            threads=True,
            progress=False,
            prepost=True,
            auto_adjust=False
        )

        for ticker in symbols:

            try:

                daily = get_ticker_data(
                    daily_data,
                    ticker
                )

                intraday = get_ticker_data(
                    intraday_data,
                    ticker
                )

                if daily.empty:
                    continue

                daily = daily.dropna(
                    subset=["Close"]
                )

                if daily.empty:
                    continue

                latest_daily = daily.iloc[-1]

                latest_daily_close = float(
                    latest_daily["Close"]
                )

                latest_daily_date = pd.Timestamp(
                    daily.index[-1]
                ).date()

                today_row_exists = (
                    latest_daily_date == today_et
                )

                close_pending = (
                    today_row_exists
                    and now_et.hour < 16
                )

                if close_pending:
                    official_close = None
                else:
                    official_close = latest_daily_close

                if len(daily) >= 2:
                    prev_close = float(
                        daily.iloc[-2]["Close"]
                    )
                else:
                    prev_close = latest_daily_close

                current_price = None

                if not intraday.empty:

                    intraday = intraday.dropna(
                        subset=["Close"]
                    )

                    if not intraday.empty:
                        current_price = float(
                            intraday.iloc[-1]["Close"]
                        )

                if current_price is None:
                    current_price = latest_daily_close

                reference_price = (
                    current_price
                    if close_pending
                    else official_close
                )

                if reference_price is None:
                    reference_price = current_price

                change = reference_price - prev_close

                change_pct = (
                    change / prev_close * 100
                    if prev_close != 0
                    else 0.0
                )

                volume = 0

                if (
                    "Volume" in latest_daily
                    and not pd.isna(latest_daily["Volume"])
                ):
                    volume = int(
                        latest_daily["Volume"]
                    )

                ticker_obj = yf.Ticker(ticker)

                info = getattr(
                    ticker_obj,
                    "fast_info",
                    None
                )

                market_cap = 0

                if info:
                    try:
                        market_cap = info.get(
                            "market_cap",
                            0
                        ) or 0
                    except Exception:
                        market_cap = 0

                if not market_cap:
                    try:
                        full_info = ticker_obj.info
                        market_cap = full_info.get(
                            "marketCap",
                            0
                        ) or 0
                    except Exception:
                        market_cap = 0

                market_cap = float(
                    market_cap or 0
                )

                result.append({

                    "종목명": KOREAN_NAMES.get(
                        ticker,
                        ticker
                    ),

                    "티커": ticker.replace("-", "."),

                    "현재가": current_price,

                    "종가": official_close,

                    "종가확정대기": close_pending,

                    "등락": change,

                    "등락률": change_pct,

                    "시가총액": format_market_cap(
                        market_cap
                    ),

                    "시총숫자": market_cap,

                    "거래량": f"{volume:,}"

                })

            except Exception:
                continue

    except Exception as e:

        st.error(
            f"주식 데이터 다운로드 오류: {e}"
        )

    return pd.DataFrame(result)


# ==========================================
# 필라델피아 반도체 지수 수집
# ==========================================

@st.cache_data(ttl=60)
def get_sox_index_data():

    now_et = datetime.now(
        ZoneInfo("America/New_York")
    )

    result = {
        "현재가": None,
        "종가": None,
        "전일종가": None,
        "등락": None,
        "등락률": None,
        "종가확정대기": False,
        "오류": None
    }

    try:

        ticker = yf.Ticker("^SOX")

        daily = ticker.history(
            period="5d",
            interval="1d"
        )

        if daily.empty:
            result["오류"] = "지수 일봉 데이터를 가져오지 못했습니다."
            return result

        daily = daily.dropna(
            subset=["Close"]
        )

        if daily.empty:
            result["오류"] = "지수 종가 데이터가 없습니다."
            return result

        latest_daily = daily.iloc[-1]

        latest_close = float(
            latest_daily["Close"]
        )

        latest_date = pd.Timestamp(
            daily.index[-1]
        ).date()

        today_et = now_et.date()

        today_row_exists = (
            latest_date == today_et
        )

        close_pending = (
            today_row_exists
            and now_et.hour < 16
        )

        if len(daily) >= 2:
            prev_close = float(
                daily.iloc[-2]["Close"]
            )
        else:
            prev_close = latest_close

        current_price = None

        try:

            intraday = ticker.history(
                period="1d",
                interval="1m"
            )

            if not intraday.empty:

                intraday = intraday.dropna(
                    subset=["Close"]
                )

                if not intraday.empty:
                    current_price = float(
                        intraday.iloc[-1]["Close"]
                    )

        except Exception:
            current_price = None

        if current_price is None:
            current_price = latest_close

        reference_price = (
            current_price
            if close_pending
            else latest_close
        )

        change = reference_price - prev_close

        change_pct = (
            change / prev_close * 100
            if prev_close != 0
            else 0.0
        )

        result.update({

            "현재가": current_price,

            "종가": (
                None
                if close_pending
                else latest_close
            ),

            "전일종가": prev_close,

            "등락": change,

            "등락률": change_pct,

            "종가확정대기": close_pending

        })

    except Exception as e:
        result["오류"] = str(e)

    return result


# ==========================================
# 폰트 자동 조절 함수
# ==========================================

def get_fitted_font(
    font_path,
    text,
    max_size,
    max_width,
    max_height
):

    size = max_size

    while size > 10:

        try:
            font = ImageFont.truetype(
                str(font_path),
                size
            )

        except OSError:
            return ImageFont.load_default()

        bbox = font.getbbox(text)

        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if (
            width <= max_width
            and height <= max_height
        ):
            return font

        size -= 2

    return ImageFont.load_default()


# ==========================================
# 로고 찾기
# ==========================================

def find_logo(ticker):

    ticker = str(ticker)

    candidates = [
        BASE / f"{ticker}.png",
        BASE / f"{ticker.replace('.', '-')}.png",
        BASE / f"{ticker.replace('.', '_')}.png"
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


# ==========================================
# 이미지에 로고 삽입
# ==========================================

def draw_logo_or_ticker(
    img,
    draw,
    ticker,
    box,
    font_path,
    ticker_size=55
):

    x1, y1, x2, y2 = box

    logo_path = find_logo(ticker)

    if logo_path:

        try:

            logo = Image.open(
                logo_path
            ).convert("RGBA")

            logo.thumbnail(
                (x2 - x1 - 20, y2 - y1 - 20),
                Image.Resampling.LANCZOS
            )

            logo_x = (
                x1 + (x2 - x1 - logo.width) // 2
            )

            logo_y = (
                y1 + (y2 - y1 - logo.height) // 2
            )

            img.paste(
                logo,
                (logo_x, logo_y),
                logo
            )

            return

        except Exception:
            pass

    font = get_fitted_font(
        font_path,
        ticker,
        ticker_size,
        x2 - x1 - 20,
        y2 - y1 - 20
    )

    bbox = draw.textbbox(
        (0, 0),
        ticker,
        font=font
    )

    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.text(
        (
            x1 + (x2 - x1 - tw) / 2,
            y1 + (y2 - y1 - th) / 2 - bbox[1]
        ),
        ticker,
        font=font,
        fill=(20, 20, 20)
    )


# ==========================================
# 등락률 표시 함수
# 상승: 빨간색 위쪽 삼각형
# 하락: 파란색 아래쪽 삼각형
# ==========================================

def draw_change(
    draw,
    font_path,
    pct,
    arrow_x,
    pct_right,
    y1,
    y2,
    font_size=70,
    arrow_size=48,
    text_width=205
):

    if pct is None or pd.isna(pct):
        return

    pct = float(pct)

    color = (
        (238, 42, 58)
        if pct >= 0
        else (0, 111, 218)
    )

    pct_text = f"{abs(pct):.2f}%"

    pct_font = get_fitted_font(
        font_path,
        pct_text,
        font_size,
        text_width,
        y2 - y1 - 15
    )

    bbox = draw.textbbox(
        (0, 0),
        pct_text,
        font=pct_font
    )

    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    center_y = (y1 + y2) / 2

    triangle_width = arrow_size
    triangle_height = arrow_size

    if pct >= 0:
        # 위쪽 삼각형
        triangle = [
            (arrow_x + triangle_width / 2, center_y - triangle_height / 2),
            (arrow_x, center_y + triangle_height / 2),
            (arrow_x + triangle_width, center_y + triangle_height / 2)
        ]
    else:
        # 아래쪽 삼각형
        triangle = [
            (arrow_x, center_y - triangle_height / 2),
            (arrow_x + triangle_width, center_y - triangle_height / 2),
            (arrow_x + triangle_width / 2, center_y + triangle_height / 2)
        ]

    draw.polygon(
        triangle,
        fill=color
    )

    draw.text(
        (
            pct_right - tw,
            center_y - th / 2 - bbox[1]
        ),
        pct_text,
        font=pct_font,
        fill="white"
    )


# ==========================================
# 기존 시가총액 TOP10 CG
# ==========================================

def make_cg_image(rows):

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"CG 템플릿을 찾을 수 없습니다: {TEMPLATE_PATH}"
        )

    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"폰트를 찾을 수 없습니다: {FONT_PATH}"
        )

    img = Image.open(
        TEMPLATE_PATH
    ).convert("RGB")

    draw = ImageDraw.Draw(img)

    y_ranges = [
        (310, 423),
        (430, 541),
        (548, 659),
        (666, 777),
        (784, 902)
    ]

    for (y1, y2), row in zip(
        y_ranges,
        rows[:5]
    ):

        ticker = str(row["티커"])

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

        draw_logo_or_ticker(
            img,
            draw,
            ticker,
            (200, y1 + 5, 470, y2 - 5),
            FONT_PATH
        )

        name = f'{row["종목명"]}({ticker})'

        name_font = get_fitted_font(
            FONT_PATH,
            name,
            65,
            750,
            y2 - y1 - 15
        )

        bbox = draw.textbbox(
            (0, 0),
            name,
            font=name_font
        )

        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        draw.text(
            (
                880 - tw / 2,
                y1 + (y2 - y1 - th) / 2 - bbox[1]
            ),
            name,
            font=name_font,
            fill="white"
        )

        draw_change(
            draw,
            FONT_PATH,
            row["등락률"],
            1300,
            1710,
            y1,
            y2
        )

    output = BytesIO()

    img.save(
        output,
        format="PNG"
    )

    return output.getvalue()


# ==========================================
# 반도체 지수 + 구성종목 CG
# 왼쪽: 지수 등락률 1개
# 오른쪽: 종목별 등락률 5개
# 종목 로고는 표시하지 않음
# ==========================================

def make_sox_cg_image(rows, index_data, template_path):

    if not template_path.exists():
        raise FileNotFoundError(
            f"필반 CG 템플릿을 찾을 수 없습니다: {template_path}"
        )

    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"폰트를 찾을 수 없습니다: {FONT_PATH}"
        )

    # 업로드한 원본 CG를 그대로 사용합니다.
    # 제목, 종목명, 배경, 박스 위치는 다시 그리지 않고 등락률만 덧씌웁니다.
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 1920x1080 원본 이미지 기준 종목별 행 위치
    y_ranges = [
        (202, 326),
        (340, 464),
        (478, 602),
        (616, 740),
        (754, 880)
    ]

    # 오른쪽 종목별 등락률
    for (y1, y2), row in zip(y_ranges, rows[:5]):
        draw_change(
            draw,
            FONT_PATH,
            row.get("등락률"),
            1390,
            1705,
            y1,
            y2
        )

    # 왼쪽 필라델피아 반도체 지수 등락률
    index_pct = index_data.get("등락률")

    if index_pct is not None and pd.notna(index_pct):
        draw_change(
            draw,
            FONT_PATH,
            index_pct,
            210,
            545,
            640,
            740,
            font_size=96,
            arrow_size=68,
            text_width=255
        )
    else:
        no_data_font = get_fitted_font(
            FONT_PATH,
            "데이터 없음",
            38,
            350,
            60
        )
        bbox = draw.textbbox((0, 0), "데이터 없음", font=no_data_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (365 - tw / 2, 690 - th / 2 - bbox[1]),
            "데이터 없음",
            font=no_data_font,
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

[data-testid="stMetricValue"] {
    color: white;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# 홈페이지 제목
# ==========================================

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
        get_sox_index_data.clear()

        st.rerun()

with c2:

    now = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).strftime("%Y-%m-%d %H:%M:%S")

    st.caption(
        f"접속 기준 시각: {now} (KST)"
    )


# ==========================================
# 데이터 수집 및 출력
# ==========================================

try:

    with st.spinner(
        "야후 파이낸스에서 데이터를 가져오는 중입니다..."
    ):

        df = get_market_quotes(SYMBOLS)

        sox_df = get_market_quotes(SOX_SYMBOLS)

        sox_index = get_sox_index_data()

    if df.empty:

        st.error(
            "시가총액 데이터를 가져오지 못했습니다. "
            "잠시 후 새로고침해 주세요."
        )

        st.stop()

    # ======================================
    # 시가총액 TOP10 정렬
    # ======================================

    df = df[
        df["시총숫자"] > 0
    ].copy()

    df = (
        df.sort_values(
            "시총숫자",
            ascending=False
        )
        .drop_duplicates("티커")
        .reset_index(drop=True)
    )

    df.insert(
        0,
        "순위",
        range(1, len(df) + 1)
    )

    top10 = df.head(10).copy()

    # ======================================
    # 반도체 10개 정렬
    # ======================================

    if not sox_df.empty:

        sox_df = sox_df[
            sox_df["시총숫자"] > 0
        ].copy()

        sox_df = (
            sox_df.sort_values(
                "시총숫자",
                ascending=False
            )
            .drop_duplicates("티커")
            .reset_index(drop=True)
        )

        sox_df.insert(
            0,
            "순위",
            range(1, len(sox_df) + 1)
        )

    # ======================================
    # MARKET OVERVIEW
    # ======================================

    st.subheader("MARKET OVERVIEW")

    st.info(
        "등록된 주요 대형주 후보 종목 내 시가총액 순위입니다."
    )

    st.divider()

    # ======================================
    # US MARKET CAP TOP 10
    # ======================================

    st.subheader("🏆 US MARKET CAP TOP 10")

    st.caption(
        "야후 파이낸스 기준 시가총액 순위"
    )

    display = top10[
        [
            "순위",
            "종목명",
            "티커",
            "현재가",
            "종가",
            "등락",
            "등락률",
            "시가총액",
            "거래량"
        ]
    ].copy()

    display["현재가"] = display["현재가"].map(
        lambda x: f"${x:,.2f}"
        if pd.notna(x)
        else "-"
    )

    display["종가"] = display["종가"].map(
        lambda x: f"${x:,.2f}"
        if pd.notna(x)
        else "-"
    )

    display["등락"] = display["등락"].map(
        lambda x: f"{x:+,.2f}"
        if pd.notna(x)
        else "-"
    )

    display["등락률"] = display["등락률"].map(
        lambda x: f"{x:+.2f}%"
        if pd.notna(x)
        else "-"
    )

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "현재가: 최신 1분봉 기준 (프리마켓·애프터마켓 포함 가능) | "
        "종가: 당일 정규장 마감 가격"
    )

    st.divider()

    # ======================================
    # 기존 시가총액 CG
    # ======================================

    st.subheader("📺 US MARKET CAP 방송용 CG")

    st.caption(
        "시가총액 1~5위와 6~10위 각각 1920×1080 PNG"
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

    # ======================================
    # 기존 시가총액 그래프
    # ======================================

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

    st.divider()

    # ======================================
    # PHILADELPHIA SEMICONDUCTOR INDEX
    # ======================================

    st.subheader(
        "💻 PHILADELPHIA SEMICONDUCTOR INDEX"
    )

    st.caption(
        "필라델피아 반도체 지수 | Yahoo Finance: ^SOX"
    )

    if sox_index.get("오류"):

        st.warning(
            f"반도체 지수 데이터를 가져오지 못했습니다: "
            f"{sox_index['오류']}"
        )

    else:

        m1, m2, m3, m4 = st.columns(4)

        with m1:

            st.metric(
                "SOX 지수",
                (
                    f"{sox_index['현재가']:,.2f}"
                    if sox_index["현재가"] is not None
                    else "-"
                )
            )

        with m2:

            st.metric(
                "전일 종가",
                (
                    f"{sox_index['전일종가']:,.2f}"
                    if sox_index["전일종가"] is not None
                    else "-"
                )
            )

        with m3:

            st.metric(
                "등락",
                (
                    f"{sox_index['등락']:+,.2f}"
                    if sox_index["등락"] is not None
                    else "-"
                )
            )

        with m4:

            st.metric(
                "등락률",
                (
                    f"{sox_index['등락률']:+.2f}%"
                    if sox_index["등락률"] is not None
                    else "-"
                )
            )

    st.divider()

    # ======================================
    # 반도체 구성종목 10개
    # ======================================

    st.subheader(
        "🔬 SEMICONDUCTOR TOP 10"
    )

    st.caption(
        "고정 구성종목 10개 | 시가총액 기준 정렬"
    )

    if sox_df.empty:

        st.warning(
            "반도체 구성종목 데이터를 가져오지 못했습니다."
        )

    else:

        sox_display = sox_df[
            [
                "순위",
                "종목명",
                "티커",
                "현재가",
                "종가",
                "등락",
                "등락률",
                "시가총액",
                "거래량"
            ]
        ].copy()

        sox_display["현재가"] = sox_display["현재가"].map(
            lambda x: f"${x:,.2f}"
            if pd.notna(x)
            else "-"
        )

        sox_display["종가"] = sox_display["종가"].map(
            lambda x: f"${x:,.2f}"
            if pd.notna(x)
            else "-"
        )

        sox_display["등락"] = sox_display["등락"].map(
            lambda x: f"{x:+,.2f}"
            if pd.notna(x)
            else "-"
        )

        sox_display["등락률"] = sox_display["등락률"].map(
            lambda x: f"{x:+.2f}%"
            if pd.notna(x)
            else "-"
        )

        st.dataframe(
            sox_display,
            hide_index=True,
            use_container_width=True
        )

        st.caption(
            "구성종목은 지정된 10개 종목으로 고정되며, "
            "표시 순위는 수집된 시가총액을 기준으로 합니다."
        )

    st.divider()

    # ======================================
    # 반도체 시가총액 그래프
    # ======================================

    st.subheader(
        "SEMICONDUCTOR MARKET CAP RANKING"
    )

    if not sox_df.empty:

        sox_chart_df = sox_df.sort_values(
            "시총숫자",
            ascending=True
        )

        sox_fig = px.bar(
            sox_chart_df,
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

        sox_fig.update_layout(
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
            sox_fig,
            use_container_width=True
        )

    st.divider()

    # ======================================
    # 반도체 방송용 CG
    # ======================================

    st.subheader(
        "📺 SEMICONDUCTOR 방송용 CG"
    )

    st.caption(
        "업로드한 필반 1장·2장 원본 CG를 그대로 사용하고, "
        "왼쪽에는 지수 등락률 1개, 오른쪽에는 종목별 등락률을 표시합니다."
    )

    if not sox_df.empty:

        # 데이터프레임을 티커 기준으로 조회해 원본 이미지에 인쇄된 순서대로 배치합니다.
        sox_rows_by_ticker = {
            str(row["티커"]): row
            for row in sox_df.to_dict("records")
        }

        sox_page1_rows = [
            sox_rows_by_ticker[ticker]
            for ticker in SOX_PAGE1_ORDER
            if ticker in sox_rows_by_ticker
        ]

        sox_page2_rows = [
            sox_rows_by_ticker[ticker]
            for ticker in SOX_PAGE2_ORDER
            if ticker in sox_rows_by_ticker
        ]

        sox_page1 = make_sox_cg_image(
            sox_page1_rows,
            sox_index,
            SOX_TEMPLATE_1
        )

        sox_page2 = make_sox_cg_image(
            sox_page2_rows,
            sox_index,
            SOX_TEMPLATE_2
        )

        sox_a, sox_b = st.columns(2)

        with sox_a:

            st.image(
                sox_page1,
                caption="1장 | 필라델피아 반도체 구성종목",
                use_container_width=True
            )

            st.download_button(
                "반도체 1장 PNG 저장",
                sox_page1,
                "semiconductor_top10_1-5.png",
                "image/png",
                use_container_width=True
            )

        with sox_b:

            st.image(
                sox_page2,
                caption="2장 | 필라델피아 반도체 구성종목",
                use_container_width=True
            )

            st.download_button(
                "반도체 2장 PNG 저장",
                sox_page2,
                "semiconductor_top10_6-10.png",
                "image/png",
                use_container_width=True
            )

    st.divider()

    # ======================================
    # 전체 수집 종목
    # ======================================

    with st.expander(
        "전체 수집 종목 확인"
    ):

        st.dataframe(
            df[
                [
                    "순위",
                    "종목명",
                    "티커",
                    "현재가",
                    "종가",
                    "등락률",
                    "시가총액",
                    "거래량"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

    # ======================================
    # 하단 정보
    # ======================================

    st.caption(
        f"시가총액 후보 수집 종목: {len(df)}개 | "
        f"반도체 구성종목 수집: {len(sox_df)}개 | "
        f"데이터 출처: Yahoo Finance | "
        f"화면 갱신: {now} KST"
    )


except Exception as e:

    st.error(
        f"데이터 수집 또는 CG 생성 중 오류가 발생했습니다: {e}"
    )

    st.info(
        "인터넷 연결, CG 템플릿 파일명, 폰트 파일명을 확인해 주세요."
    )
