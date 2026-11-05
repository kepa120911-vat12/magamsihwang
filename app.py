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
BASE = Path(__file__).parent
CNBC_URL = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cnbc.com/"}

SYMBOLS = [
    "NVDA","AAPL","MSFT","AMZN","GOOGL","META","AVGO","BRK.B","TSLA","LLY",
    "WMT","JPM","V","ORCL","NFLX","XOM","MA","COST","JNJ","ABBV","PLTR","AMD",
    "BAC","KO","GE","CAT","CSCO","HD","PG","CRM","CVX","IBM","MRK","PM","GS",
    "MS","AXP","UNH","TMO","LIN","MCD","PEP","RTX","INTU","DIS","UBER","NOW",
    "QCOM","TXN"
]
KOREAN_NAMES = {
    "NVDA":"엔비디아","AAPL":"애플","MSFT":"마이크로소프트","AMZN":"아마존",
    "GOOGL":"알파벳","META":"메타","AVGO":"브로드컴","BRK.B":"버크셔 해서웨이",
    "TSLA":"테슬라","LLY":"일라이 릴리","WMT":"월마트","JPM":"JP모건","V":"비자",
    "ORCL":"오라클","NFLX":"넷플릭스","XOM":"엑슨모빌","MA":"마스터카드",
    "COST":"코스트코","JNJ":"존슨앤드존슨","ABBV":"애브비","PLTR":"팔란티어",
    "AMD":"AMD","BAC":"뱅크오브아메리카","KO":"코카콜라","GE":"GE 에어로스페이스",
    "CAT":"캐터필러","CSCO":"시스코","HD":"홈디포","PG":"프록터앤드갬블",
    "CRM":"세일즈포스","CVX":"셰브론","IBM":"IBM","MRK":"머크","PM":"필립모리스",
    "GS":"골드만삭스","MS":"모건스탠리","AXP":"아메리칸 익스프레스",
    "UNH":"유나이티드헬스","TMO":"써모 피셔","LIN":"린데","MCD":"맥도날드",
    "PEP":"펩시코","RTX":"RTX","INTU":"인튜이트","DIS":"디즈니","UBER":"우버",
    "NOW":"서비스나우","QCOM":"퀄컴","TXN":"텍사스 인스트루먼트"
}

@st.cache_data(ttl=60)
def get_cnbc_quotes(symbols):
    params = {"symbols":"|".join(symbols),"requestMethod":"itv","noform":"1",
              "partnerId":"2","fund":"1","exthrs":"1","output":"json","events":"1"}
    response = requests.get(CNBC_URL,params=params,headers=HEADERS,timeout=30)
    response.raise_for_status()
    quotes=response.json().get("FormattedQuoteResult",{}).get("FormattedQuote",[])
    if isinstance(quotes,dict): quotes=[quotes]
    result=[]
    for q in quotes:
        try:
            ticker=q.get("symbol","").strip()
            pct=str(q.get("change_pct","0")).replace("%","").replace(",","").replace("+","")
            result.append({
                "종목명":KOREAN_NAMES.get(ticker,q.get("name",ticker)),
                "티커":ticker,
                "종가":float(str(q.get("last","0")).replace(",","")),
                "등락":float(str(q.get("change","0")).replace(",","")),
                "등락률":float(pct),
                "시가총액":q.get("mktcapView",""),
                "거래량":q.get("volume","")
            })
        except (ValueError,TypeError):
            continue
    return pd.DataFrame(result)

def market_cap_to_number(value):
    value=str(value or "").upper().replace(",","").strip()
    try:
        if value.endswith("T"): return float(value[:-1])*1e12
        if value.endswith("B"): return float(value[:-1])*1e9
        if value.endswith("M"): return float(value[:-1])*1e6
        return float(value)
    except ValueError:
        return 0

def fit_font(draw,text,font_path,max_size,max_width,min_size=25):
    for size in range(max_size,min_size-1,-1):
        font=ImageFont.truetype(str(font_path),size)
        box=draw.textbbox((0,0),text,font=font)
        if box[2]-box[0] <= max_width: return font
    return ImageFont.truetype(str(font_path),min_size)

def make_cg_image(rows,page_number):
    """원본 CG의 5개 행에 로고 이미지와 텍스트를 함께 그려 잔상과 중복을 방지합니다."""
    template_path=BASE/"market_cap_template.jpg"
    font_path=BASE/"NanumGothic.ttf"
    img=Image.open(template_path).convert("RGB")
    draw=ImageDraw.Draw(img)
    
    # 1920x1080 원본 템플릿의 실제 행 위치
    y_ranges=[(310,423),(430,541),(548,659),(666,777),(784,902)]
    for (y1,y2),row in zip(y_ranges,rows[:5]):
        ticker=str(row["티커"])
        
        # 각 행의 영역 초기화
        draw.rectangle((190,y1,480,y2),fill=(255,255,255))
        draw.rectangle((480,y1,1280,y2),fill=(3,23,78))
        draw.rectangle((1280,y1,1730,y2),fill=(5,10,27))
        draw.line((190,y2,1730,y2),fill=(30,70,125),width=3)

        # 종목별 로고 이미지 합성 시도 (예: NVDA.png, AAPL.png ...)
        logo_path=BASE/f"{ticker}.png"
        if logo_path.exists():
            try:
                logo_img=Image.open(logo_path).convert("RGBA")
                target_height=80  # 로고 목표 높이 설정
                h_ratio=target_height/logo_img.height
                new_width=int(logo_img.width*h_ratio)
                new_height=target_height
                logo_img=logo_img.resize((new_width,new_height),Image.Resampling.LANCZOS)

                # 로고 영역(190~480)의 정중앙에 배치
                box_center_x=(190+480)//2
                box_center_y=y1+(y2-y1)//2
                logo_x=box_center_x-(new_width//2)
                logo_y=box_center_y-(new_height//2)

                # 투명 배경(PNG 알파 채널) 유지하며 합성
                img.paste(logo_img,(logo_x,logo_y),logo_img)
            except Exception:
                # 로고 로드 중 에러 발생 시 텍스트(티커)로 대체
                ticker_font=fit_font(draw,ticker,font_path,42,250,26)
                b=draw.textbbox((0,0),ticker,font=ticker_font)
                tw,th=b[2]-b[0],b[3]-b[1]
                draw.text((335-tw/2,y1+(y2-y1-th)/2-b[1]),ticker,font=ticker_font,fill=(20,20,20))
        else:
            # 로고 파일이 없을 경우 기존처럼 티커 글자 출력
            ticker_font=fit_font(draw,ticker,font_path,42,250,26)
            b=draw.textbbox((0,0),ticker,font=ticker_font)
            tw,th=b[2]-b[0],b[3]-b[1]
            draw.text((335-tw/2,y1+(y2-y1-th)/2-b[1]),ticker,font=ticker_font,fill=(20,20,20))

        # 종목명 출력
        name=f'{row["종목명"]}({ticker})'
        name_font=fit_font(draw,name,font_path,56,750,30)
        b=draw.textbbox((0,0),name,font=name_font)
        tw,th=b[2]-b[0],b[3]-b[1]
        draw.text((880-tw/2,y1+(y2-y1-th)/2-b[1]),name,font=name_font,fill="white")

        # 등락률 출력
        pct=float(row["등락률"])
        color=(238,42,58) if pct>=0 else (0,111,218)
        arrow="▲" if pct>=0 else "▼"
        arrow_font=ImageFont.truetype(str(font_path),67)
        draw.text((1335,y1+18),arrow,font=arrow_font,fill=color)
        pct_text=f"{abs(pct):.2f}%"
        pct_font=fit_font(draw,pct_text,font_path,67,230,42)
        b=draw.textbbox((0,0),pct_text,font=pct_font)
        tw,th=b[2]-b[0],b[3]-b[1]
        draw.text((1690-tw,y1+(y2-y1-th)/2-b[1]),pct_text,font=pct_font,fill="white")

    output=BytesIO()
    img.save(output,format="PNG")
    return output.getvalue()

st.markdown("""
<style>
.stApp{background:#07111f;color:#fff}
.block-container{padding-top:2rem;padding-bottom:2rem}
h1,h2,h3{color:#fff}
</style>
""",unsafe_allow_html=True)
st.title("🇺🇸 US MARKET DASHBOARD")
st.caption("GLOBAL STOCK MARKET DATA | SOURCE: CNBC")
c1,c2=st.columns([1,5])
with c1:
    if st.button("🔄 데이터 새로고침",use_container_width=True):
        get_cnbc_quotes.clear()
        st.rerun()
with c2:
    now=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"접속 기준 시각: {now} (KST)")

try:
    with st.spinner("CNBC에서 데이터를 가져오는 중입니다..."):
        df=get_cnbc_quotes(SYMBOLS)
    if df.empty:
        st.error("CNBC에서 종목 데이터를 가져오지 못했습니다.")
        st.stop()
    df["시총숫자"]=df["시가총액"].apply(market_cap_to_number)
    df=df[df["시총숫자"]>0].copy()
    df=df.sort_values("시총숫자",ascending=False).drop_duplicates("티커").reset_index(drop=True)
    df.insert(0,"순위",range(1,len(df)+1))
    top10=df.head(10).copy()

    st.subheader("MARKET OVERVIEW")
    st.info("현재 등록된 주요 대형주 후보 종목 내 시가총액 순위입니다. 미국 전체 상장기업 전수 순위는 아닙니다.")
    st.divider()
    st.subheader("🏆 US MARKET CAP TOP 10")
    st.caption("CNBC 제공 시가총액 기준 | 등록 후보 종목 내 순위")
    display=top10[["순위","종목명","티커","종가","등락","등락률","시가총액","거래량"]].copy()
    display["종가"]=display["종가"].map(lambda x:f"${x:,.2f}")
    display["등락"]=display["등락"].map(lambda x:f"{x:+,.2f}")
    display["등락률"]=display["등락률"].map(lambda x:f"{x:+.2f}%")
    st.dataframe(display,hide_index=True,use_container_width=True)

    st.divider()
    st.subheader("📺 방송용 CG 이미지")
    st.caption("시가총액 1~5위와 6~10위를 각각 1920×1080 PNG로 생성합니다.")
    page1=make_cg_image(top10.iloc[:5].to_dict("records"),1)
    page2=make_cg_image(top10.iloc[5:10].to_dict("records"),2)
    a,b=st.columns(2)
    with a:
        st.image(page1,caption="1장 | 시가총액 1~5위",use_container_width=True)
        st.download_button("1장 PNG 저장",page1,"us_market_cap_top10_1-5.png","image/png",use_container_width=True)
    with b:
        st.image(page2,caption="2장 | 시가총액 6~10위",use_container_width=True)
        st.download_button("2장 PNG 저장",page2,"us_market_cap_top10_6-10.png","image/png",use_container_width=True)

    st.divider()
    st.subheader("MARKET CAP RANKING")
    chart_df=top10.sort_values("시총숫자",ascending=True)
    fig=px.bar(chart_df,x="시총숫자",y="티커",orientation="h",text="시가총액",
               template="plotly_dark",labels={"시총숫자":"Market Cap (USD)","티커":"Ticker"})
    fig.update_layout(paper_bgcolor="#07111f",plot_bgcolor="#07111f",font_color="white",
                      height=450,margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig,use_container_width=True)
    with st.expander("전체 수집 종목 확인"):
        st.dataframe(df[["순위","종목명","티커","종가","등락률","시가총액","거래량"]],
                     hide_index=True,use_container_width=True)
    st.caption(f"수집 종목: {len(df)}개 | 데이터 출처: CNBC | 화면 갱신: {now} KST")
except Exception as e:
    st.error(f"데이터 수집 또는 CG 생성 중 오류가 발생했습니다: {e}")
    st.info("인터넷 연결, CNBC 데이터 응답, CG 템플릿/폰트 파일을 확인해 주세요.")