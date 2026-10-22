
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==================================================
# 1. 기본 설정
# ==================================================
st.set_page_config(
    page_title="CINEMA BOX OFFICE",
    page_icon="🎬",
    layout="wide"
)

BOXOFFICE_URL = (
    "https://kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
)
MOVIE_INFO_URL = (
    "https://kobis.or.kr/kobisopenapi/"
    "webservice/rest/movie/searchMovieInfo.json"
)

# ==================================================
# 2. 영화관 스타일 디자인
# ==================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');

.stApp {
    background:
        radial-gradient(ellipse at 50% 0%,
            rgba(180, 15, 40, 0.28), transparent 45%),
        radial-gradient(ellipse at 0% 40%,
            rgba(35, 55, 110, 0.20), transparent 40%),
        linear-gradient(180deg, #080a13, #141626 55%, #070810);
    color: #f5f5f7;
    font-family: 'Noto Sans KR', sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(7, 8, 16, 0.55);
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.hero {
    text-align: center;
    padding: 38px 15px 30px;
    margin-bottom: 25px;
    border-bottom: 1px solid rgba(255,255,255,0.13);
    background: radial-gradient(
        ellipse at center,
        rgba(190,15,40,0.17), transparent 70%);
}

.hero-kicker {
    color: #f04460;
    font-size: 12px;
    letter-spacing: 5px;
    font-weight: 700;
}

.hero-title {
    font-family: 'Black Han Sans', sans-serif;
    font-size: clamp(35px, 5vw, 65px);
    letter-spacing: 3px;
    color: white;
    text-shadow: 0 0 25px rgba(230,25,55,0.35);
    margin-top: 10px;
}

.hero-subtitle {
    color: #b5b9cb;
    font-size: 14px;
    margin-top: 12px;
}

.section-title {
    color: white;
    font-size: 21px;
    font-weight: 800;
    border-left: 4px solid #e52b48;
    padding-left: 12px;
    margin: 28px 0 16px;
}

.movie-card {
    background: linear-gradient(
        145deg, rgba(36,39,58,0.96), rgba(17,19,32,0.96));
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 20px;
    min-height: 145px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.2);
}

.movie-label {
    color: #b4b9cc;
    font-size: 13px;
    margin-bottom: 12px;
}

.movie-value {
    color: white;
    font-size: clamp(20px, 2vw, 29px);
    font-weight: 900;
    overflow-wrap: anywhere;
}

.movie-caption {
    color: #f04460;
    font-size: 12px;
    margin-top: 10px;
}

.stSelectbox label,
.stDateInput label {
    color: #e5e7f0 !important;
    font-weight: 600;
}

div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input {
    background-color: #191c2c;
    color: white;
    border-color: #41455d;
}

.stButton > button {
    background: linear-gradient(90deg, #b81732, #ed334e);
    color: white;
    border: none;
    border-radius: 9px;
    font-weight: 700;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #d41d3b, #ff5269);
    color: white;
}

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    overflow: hidden;
}

.footer {
    text-align: center;
    color: #858ba0;
    font-size: 12px;
    padding: 25px 0 5px;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin-top: 35px;
}
</style>
""", unsafe_allow_html=True)


# ==================================================
# 3. API 데이터 처리 함수
# ==================================================
def check_api_response(data):
    """KOBIS API 오류 응답 확인"""
    if "faultInfo" in data:
        fault = data["faultInfo"]

        if isinstance(fault, dict):
            message = fault.get("message", "API 요청에 실패했습니다.")
        else:
            message = str(fault)

        raise ValueError(message)


@st.cache_data(ttl=1800, show_spinner=False)
def get_daily_boxoffice(api_key, target_date):
    """선택한 날짜의 일별 박스오피스"""
    response = requests.get(
        BOXOFFICE_URL,
        params={
            "key": api_key,
            "targetDt": target_date,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    check_api_response(data)

    result = data.get("boxOfficeResult", {})
    return result.get("dailyBoxOfficeList", [])


@st.cache_data(ttl=86400, show_spinner=False)
def get_movie_genres(api_key, movie_code):
    """영화 상세정보에서 장르 목록 가져오기"""
    if not movie_code:
        return []

    response = requests.get(
        MOVIE_INFO_URL,
        params={
            "key": api_key,
            "movieCd": str(movie_code),
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    check_api_response(data)

    movie_info = (
        data.get("movieInfoResult", {})
        .get("movieInfo", {})
    )

    genres = movie_info.get("genres") or []

    return sorted({
        str(item.get("genreNm", "")).strip()
        for item in genres
        if isinstance(item, dict)
        and item.get("genreNm")
    })


def to_int(value):
    """숫자 문자열을 안전하게 정수로 변환"""
    try:
        return int(float(str(value or "0").replace(",", "")))
    except (ValueError, TypeError):
        return 0


# ==================================================
# 4. 제목 및 API 키
# ==================================================
st.markdown("""
<div class="hero">
    <div class="hero-kicker">KOREAN BOX OFFICE · DAILY CHART</div>
    <div class="hero-title">CINEMA BOX OFFICE</div>
    <div class="hero-subtitle">
        오늘의 영화 순위부터 장르별 관객 데이터까지
    </div>
</div>
""", unsafe_allow_html=True)

try:
    API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    st.error(
        "KOBIS API 키를 찾을 수 없습니다. "
        "Streamlit Cloud의 Settings → Secrets에서 "
        "KOBIS_KEY를 등록해 주세요."
    )
    st.code('KOBIS_KEY = "본인의_API_키"')
    st.stop()


# ==================================================
# 5. 날짜 선택 및 새로고침
# ==================================================
today_korea = datetime.now(ZoneInfo("Asia/Seoul")).date()
yesterday = today_korea - timedelta(days=1)

date_col, refresh_col = st.columns([4, 1])

with date_col:
    selected_date = st.date_input(
        "📅 박스오피스 조회 날짜",
        value=yesterday,
        min_value=datetime(2004, 1, 1).date(),
        max_value=yesterday,
        format="YYYY/MM/DD",
    )

with refresh_col:
    st.write("")
    st.write("")
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ==================================================
# 6. 일별 박스오피스 불러오기
# ==================================================
target_date = selected_date.strftime("%Y%m%d")

try:
    with st.spinner("🎬 박스오피스 데이터를 불러오는 중입니다..."):
        raw_movies = get_daily_boxoffice(API_KEY, target_date)

except (requests.RequestException, ValueError, KeyError) as error:
    st.error(f"박스오피스 데이터를 불러오지 못했습니다: {error}")
    st.info(
        "API 키, 인터넷 연결 및 KOBIS API 응답을 확인해 주세요."
    )
    st.stop()

if not raw_movies:
    st.warning("그날은 아직 집계 전입니다")
    st.stop()


# ==================================================
# 7. 영화별 장르 정보 추가
# ==================================================
movies = []
genre_lookup_failed = False

with st.spinner("🎞️ 영화별 장르 정보를 확인하고 있습니다..."):
    for item in raw_movies:
        movie_code = item.get("movieCd", "")

        try:
            genre_list = get_movie_genres(API_KEY, movie_code)
        except (requests.RequestException, ValueError, KeyError):
            genre_list = []
            genre_lookup_failed = True

        movie_name = item.get("movieNm", "영화 제목 없음")
        audi_cnt = to_int(item.get("audiCnt"))
        audi_acc = to_int(item.get("audiAcc"))
        scrn_cnt = to_int(item.get("scrnCnt"))
        rank = to_int(item.get("rank"))
        rank_inten = to_int(item.get("rankInten"))

        genre_text = ", ".join(genre_list) if genre_list else "정보 없음"

        display_name = (
            f"🏆 {movie_name}" if audi_acc >= 1_000_000
            else movie_name
        )

        if rank_inten > 0:
            rank_change = f"↑ {rank_inten}"
        elif rank_inten < 0:
            rank_change = f"↓ {abs(rank_inten)}"
        else:
            rank_change = "—"

        movies.append({
            "순위": rank,
            "순위 변동": rank_change,
            "영화명": movie_name,
            "표시용 영화명": display_name,
            "장르": genre_text,
            "개봉일": item.get("openDt") or "정보 없음",
            "일일 관객수": audi_cnt,
            "누적 관객수": audi_acc,
            "스크린 수": scrn_cnt,
        })

df = pd.DataFrame(movies)

if df.empty:
    st.warning("표시할 영화 데이터가 없습니다.")
    st.stop()

if genre_lookup_failed:
    st.warning(
        "일부 영화의 장르 정보를 가져오지 못했습니다. "
        "해당 영화는 '정보 없음'으로 표시될 수 있습니다."
    )


# ==================================================
# 8. 장르 선택
# ==================================================
st.markdown(
    '<div class="section-title">🎭 장르별 영화 탐색</div>',
    unsafe_allow_html=True,
)

all_genres = sorted({
    genre.strip()
    for genre_text in df["장르"]
    for genre in genre_text.split(",")
    if genre.strip() and genre.strip() != "정보 없음"
})

genre_options = ["전체 장르"] + all_genres

if (df["장르"] == "정보 없음").any():
    genre_options.append("정보 없음")

selected_genre = st.selectbox(
    "보고 싶은 장르를 선택하세요",
    options=genre_options,
)

if selected_genre == "전체 장르":
    filtered_df = df.copy()
elif selected_genre == "정보 없음":
    filtered_df = df[df["장르"] == "정보 없음"].copy()
else:
    filtered_df = df[
        df["장르"].apply(
            lambda text: selected_genre in [
                genre.strip() for genre in text.split(",")
            ]
        )
    ].copy()

if not all_genres:
    st.info(
        "현재 조회 결과에서 장르 정보를 찾지 못했습니다. "
        "API 키와 영화 상세정보 응답을 확인해 주세요."
    )

if filtered_df.empty:
    st.info("선택한 장르에 해당하는 영화가 없습니다.")
    st.stop()


# ==================================================
# 9. 핵심 통계 카드
# ==================================================
st.markdown(
    '<div class="section-title">🍿 박스오피스 요약</div>',
    unsafe_allow_html=True,
)

top_movie = filtered_df.sort_values("순위").iloc[0]
total_audience = int(filtered_df["일일 관객수"].sum())
total_screens = int(filtered_df["스크린 수"].sum())

card1, card2, card3 = st.columns(3)

with card1:
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-label">🥇 선택 장르 최고 순위</div>
        <div class="movie-value">{top_movie['표시용 영화명']}</div>
        <div class="movie-caption">전체 박스오피스 {top_movie['순위']}위</div>
    </div>
    """, unsafe_allow_html=True)

with card2:
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-label">👥 일일 관객수 합계</div>
        <div class="movie-value">{total_audience:,}명</div>
        <div class="movie-caption">{selected_date.strftime('%Y년 %m월 %d일')} 기준</div>
    </div>
    """, unsafe_allow_html=True)

with card3:
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-label">🎥 스크린 수 합계</div>
        <div class="movie-value">{total_screens:,}개</div>
        <div class="movie-caption">선택 장르: {selected_genre}</div>
    </div>
    """, unsafe_allow_html=True)


# ==================================================
# 10. 영화별 관객수 막대그래프
# ==================================================
st.markdown(
    '<div class="section-title">📊 영화별 일일 관객수</div>',
    unsafe_allow_html=True,
)

chart_df = (
    filtered_df.sort_values("일일 관객수", ascending=False)
    .head(10)
    .copy()
)

# 영화명마다 고유한 색상을 지정
palette = px.colors.qualitative.Bold
movie_names = chart_df["표시용 영화명"].tolist()

color_map = {
    name: palette[i % len(palette)]
    for i, name in enumerate(movie_names)
}

fig = px.bar(
    chart_df,
    x="표시용 영화명",
    y="일일 관객수",
    color="표시용 영화명",
    color_discrete_map=color_map,
    text="일일 관객수",
    hover_data={
        "장르": True,
        "순위": True,
        "누적 관객수": ":,.0f",
        "스크린 수": True,
        "표시용 영화명": False,
        "일일 관객수": ":,.0f",
    },
    labels={
        "표시용 영화명": "영화",
        "일일 관객수": "일일 관객수(명)",
        "장르": "장르",
        "순위": "전체 순위",
        "누적 관객수": "누적 관객수",
        "스크린 수": "스크린 수",
    },
)

fig.update_traces(
    texttemplate="%{text:,.0f}명",
    textposition="outside",
    cliponaxis=False,
    marker_line_width=0,
    opacity=0.95,
)

fig.update_layout(
    height=500,
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(9,11,20,0.25)",
    font=dict(
        family="Noto Sans KR, sans-serif",
        color="#F5F5F7",
        size=12,
    ),
    title=dict(
        text=f"{selected_date.strftime('%Y.%m.%d')}  |  {selected_genre}",
        x=0.02,
        xanchor="left",
        font=dict(size=18, color="#FFFFFF"),
    ),
    margin=dict(l=20, r=25, t=70, b=110),
    xaxis=dict(
        title="",
        tickangle=-25,
        showgrid=False,
        tickfont=dict(color="#D8D9E3"),
        linecolor="rgba(255,255,255,0.15)",
    ),
    yaxis=dict(
        title="일일 관객수(명)",
        gridcolor="rgba(255,255,255,0.10)",
        zerolinecolor="rgba(255,255,255,0.15)",
        tickformat=",",
        tickfont=dict(color="#B9BDCE"),
        title_font=dict(color="#D8D9E3"),
    ),
    hoverlabel=dict(
        bgcolor="#1C2033",
        font_color="white",
    ),
)

st.plotly_chart(fig, use_container_width=True)


# ==================================================
# 11. 영화 상세 정보 표
# ==================================================
st.markdown(
    '<div class="section-title">🎬 영화별 상세 정보</div>',
    unsafe_allow_html=True,
)

display_df = filtered_df[
    [
        "순위",
        "순위 변동",
        "표시용 영화명",
        "장르",
        "개봉일",
        "일일 관객수",
        "누적 관객수",
        "스크린 수",
    ]
].copy()

display_df = display_df.rename(
    columns={"표시용 영화명": "영화명"}
)

for column in ["일일 관객수", "누적 관객수", "스크린 수"]:
    display_df[column] = display_df[column].map(
        lambda value: f"{value:,}"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=min(520, 40 + 38 * len(display_df)),
)

st.caption(
    "※ 장르 정보는 KOBIS 영화 상세정보 기준입니다. "
    "여러 장르에 해당하는 영화는 각 장르 필터에서 모두 표시됩니다. "
    "🏆는 누적 관객수 100만 명 이상인 영화를 뜻합니다."
)

st.markdown("""
<div class="footer">
    CINEMA BOX OFFICE · KOBIS OPEN API<br>
    영화진흥위원회 박스오피스 데이터를 활용한 영화 정보 대시보드
</div>
""", unsafe_allow_html=True)
