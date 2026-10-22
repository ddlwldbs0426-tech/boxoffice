
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="CINEMA BOX OFFICE",
    page_icon="🎬",
    layout="wide"
)

KOBIS_URL = (
    "https://kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
)

MOVIE_INFO_URL = (
    "https://kobis.or.kr/kobisopenapi/"
    "webservice/rest/movie/searchMovieInfo.json"
)

# --------------------------------------------------
# 영화관 느낌의 CSS 디자인
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');

.stApp {
    background:
        radial-gradient(ellipse at 50% 0%, rgba(150, 10, 30, 0.28), transparent 42%),
        radial-gradient(ellipse at 0% 35%, rgba(35, 55, 110, 0.22), transparent 38%),
        linear-gradient(180deg, #090b14 0%, #111321 48%, #070810 100%);
    color: #f5f5f7;
    font-family: 'Noto Sans KR', sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(7, 8, 16, 0.65);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

.hero {
    text-align: center;
    padding: 35px 20px 30px 20px;
    margin-bottom: 25px;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    background:
        radial-gradient(ellipse at center, rgba(190, 15, 40, 0.18), transparent 70%);
}

.hero-kicker {
    color: #ed4058;
    font-size: 12px;
    letter-spacing: 6px;
    font-weight: 700;
    margin-bottom: 12px;
}

.hero-title {
    font-family: 'Black Han Sans', sans-serif;
    font-size: clamp(36px, 5vw, 66px);
    letter-spacing: 3px;
    line-height: 1.2;
    color: #ffffff;
    text-shadow: 0 0 22px rgba(230, 25, 55, 0.28);
}

.hero-subtitle {
    color: #aeb2c4;
    font-size: 14px;
    margin-top: 14px;
    letter-spacing: 1px;
}

.section-title {
    font-size: 21px;
    font-weight: 800;
    color: #ffffff;
    border-left: 4px solid #e52b48;
    padding-left: 12px;
    margin-top: 25px;
    margin-bottom: 15px;
}

.movie-card {
    background: linear-gradient(145deg, rgba(36, 39, 58, 0.96), rgba(17, 19, 32, 0.96));
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 20px 22px;
    min-height: 145px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.18);
}

.movie-card-label {
    color: #aeb3c8;
    font-size: 13px;
    margin-bottom: 13px;
}

.movie-card-value {
    color: #ffffff;
    font-size: clamp(20px, 2vw, 30px);
    font-weight: 900;
    overflow-wrap: anywhere;
}

.movie-card-caption {
    color: #e94a60;
    font-size: 12px;
    margin-top: 10px;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(36,39,58,0.94), rgba(17,19,32,0.96));
    border: 1px solid rgba(255,255,255,0.10);
    padding: 18px;
    border-radius: 14px;
}

div[data-testid="stMetricLabel"] {
    color: #bfc3d4;
}

div[data-testid="stMetricValue"] {
    color: #ffffff;
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
    padding: 9px 20px;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #d41d3b, #ff5269);
    color: white;
    border: none;
}

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    overflow: hidden;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

.footer {
    text-align: center;
    color: #777d92;
    font-size: 12px;
    padding: 28px 0 5px 0;
    border-top: 1px solid rgba(255,255,255,0.10);
    margin-top: 35px;
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# API 호출 함수
# --------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_daily_boxoffice(api_key, target_date):
    """선택한 날짜의 일별 박스오피스 조회"""
    params = {
        "key": api_key,
        "targetDt": target_date,
    }

    response = requests.get(
        KOBIS_URL,
        params=params,
        timeout=20
    )
    response.raise_for_status()
    data = response.json()

    if "faultInfo" in data:
        fault = data["faultInfo"]
        raise ValueError(
            fault.get("message", "KOBIS API 요청에 실패했습니다.")
        )

    result = data.get("boxOfficeResult", {})
    return result.get("dailyBoxOfficeList", [])


@st.cache_data(ttl=86400, show_spinner=False)
def get_movie_genres(api_key, movie_code):
    """영화 상세정보에서 실제 장르 목록 조회"""
    params = {
        "key": api_key,
        "movieCd": str(movie_code),
    }

    try:
        response = requests.get(
            MOVIE_INFO_URL,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        if "faultInfo" in data:
            return []

        movie_info = (
            data.get("movieInfoResult", {})
                .get("movieInfo", {})
        )

        genres = movie_info.get("genres", [])

        return sorted({
            item.get("genreNm", "").strip()
            for item in genres
            if item.get("genreNm", "").strip()
        })

    except (requests.RequestException, ValueError, KeyError):
        return []


# --------------------------------------------------
# 제목 영역
# --------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="hero-kicker">KOREAN BOX OFFICE • DAILY CHART</div>
    <div class="hero-title">CINEMA BOX OFFICE</div>
    <div class="hero-subtitle">
        오늘의 영화 순위부터 장르별 관객 데이터까지
    </div>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# API 키 확인
# --------------------------------------------------
try:
    API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    st.error(
        "KOBIS API 키를 찾을 수 없습니다. "
        "Streamlit Cloud의 Settings → Secrets에서 "
        "KOBIS_KEY를 등록해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_API_키"')
    st.stop()


# --------------------------------------------------
# 날짜 선택
# --------------------------------------------------
today_korea = datetime.now(ZoneInfo("Asia/Seoul")).date()
yesterday = today_korea - timedelta(days=1)

col_date, col_refresh = st.columns([4, 1])

with col_date:
    selected_date = st.date_input(
        "📅 박스오피스 조회 날짜",
        value=yesterday,
        min_value=datetime(2004, 1, 1).date(),
        max_value=yesterday,
        format="YYYY/MM/DD"
    )

with col_refresh:
    st.write("")
    st.write("")
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# --------------------------------------------------
# 일별 박스오피스 데이터 불러오기
# --------------------------------------------------
target_date = selected_date.strftime("%Y%m%d")

try:
    with st.spinner("🎬 박스오피스 데이터를 불러오는 중입니다..."):
        raw_movies = get_daily_boxoffice(API_KEY, target_date)

except (requests.RequestException, ValueError, KeyError) as error:
    st.error(f"데이터를 불러오지 못했습니다: {error}")
    st.info(
        "API 키가 올바른지 확인하고 잠시 후 다시 시도해 주세요."
    )
    st.stop()

if not raw_movies:
    st.warning("그날은 아직 집계 전입니다")
    st.stop()


# --------------------------------------------------
# 데이터 정리 및 장르 정보 추가
# --------------------------------------------------
movies = []

with st.spinner("🎞️ 영화별 장르 정보를 확인하고 있습니다..."):
    for item in raw_movies:
        movie_code = item.get("movieCd", "")
        genre_list = get_movie_genres(API_KEY, movie_code)

        audi_cnt = int(item.get("audiCnt", 0) or 0)
        audi_acc = int(item.get("audiAcc", 0) or 0)
        scrn_cnt = int(item.get("scrnCnt", 0) or 0)
        rank = int(item.get("rank", 0) or 0)
        rank_inten = int(item.get("rankInten", 0) or 0)

        if genre_list:
            genre_text = ", ".join(genre_list)
        else:
            genre_text = "정보 없음"

        # 백만 관객 이상인 영화에 트로피 표시
        movie_name = item.get("movieNm", "영화 제목 없음")
        display_name = (
            f"🏆 {movie_name}"
            if audi_acc >= 1_000_000
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
            "개봉일": item.get("openDt", ""),
            "일일 관객수": audi_cnt,
            "누적 관객수": audi_acc,
            "스크린 수": scrn_cnt,
            "영화 코드": movie_code,
        })

df = pd.DataFrame(movies)

# 날짜 및 숫자 형식 정리
if not df.empty:
    df["개봉일"] = df["개봉일"].replace("", "정보 없음")
    df["일일 관객수"] = pd.to_numeric(
        df["일일 관객수"], errors="coerce"
    ).fillna(0).astype(int)
    df["누적 관객수"] = pd.to_numeric(
        df["누적 관객수"], errors="coerce"
    ).fillna(0).astype(int)
    df["스크린 수"] = pd.to_numeric(
        df["스크린 수"], errors="coerce"
    ).fillna(0).astype(int)


# --------------------------------------------------
# 장르 필터
# --------------------------------------------------
st.markdown(
    '<div class="section-title">🎭 장르별 영화 탐색</div>',
    unsafe_allow_html=True
)

all_genres = sorted({
    genre.strip()
    for genre_text in df["장르"].tolist()
    for genre in genre_text.split(",")
    if genre.strip() and genre.strip() != "정보 없음"
})

genre_options = ["전체 장르"] + all_genres

if df["장르"].eq("정보 없음").any():
    genre_options.append("정보 없음")

selected_genre = st.selectbox(
    "보고 싶은 장르를 선택하세요",
    options=genre_options,
    index=0
)

if selected_genre == "전체 장르":
    filtered_df = df.copy()
elif selected_genre == "정보 없음":
    filtered_df = df[df["장르"] == "정보 없음"].copy()
else:
    filtered_df = df[
        df["장르"].apply(
            lambda genres: selected_genre in [
                genre.strip() for genre in genres.split(",")
            ]
        )
    ].copy()

if all(df["장르"] == "정보 없음"):
    st.warning(
        "현재 영화의 장르 정보를 불러오지 못했습니다. "
        "영화별 상세정보 API 응답을 확인해 주세요."
    )


# --------------------------------------------------
# 핵심 통계 카드
# --------------------------------------------------
st.markdown(
    '<div class="section-title">🍿 오늘의 박스오피스</div>',
    unsafe_allow_html=True
)

if filtered_df.empty:
    st.info("선택한 장르에 해당하는 영화가 없습니다.")
    st.stop()

top_movie = filtered_df.sort_values(
    "순위", ascending=True
).iloc[0]

total_audience = int(filtered_df["일일 관객수"].sum())
total_screens = int(filtered_df["스크린 수"].sum())

card1, card2, card3 = st.columns(3)

with card1:
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-card-label">🥇 선택한 장르의 최고 순위</div>
        <div class="movie-card-value">{top_movie['표시용 영화명']}</div>
        <div class="movie-card-caption">
            전체 박스오피스 {top_movie['순위']}위
        </div>
    </div>
    """, unsafe_allow_html=True)

with card2:
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-card-label">👥 해당 영화들의 일일 관객수 합계</div>
        <div class="movie-card-value">{total_audience:,}명</div>
        <div class="movie-card-caption">
            {selected_date.strftime("%Y년 %m월 %d일")} 기준
        </div>
    </div>
    """, unsafe_allow_html=True)

with card3:
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-card-label">🎥 해당 영화들의 스크린 수 합계</div>
        <div class="movie-card-value">{total_screens:,}개</div>
        <div class="movie-card-caption">
            선택한 장르: {selected_genre}
        </div>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# 영화별 관객수 막대그래프
# --------------------------------------------------
st.markdown(
    '<div class="section-title">📊 영화별 일일 관객수</div>',
    unsafe_allow_html=True
)

chart_df = filtered_df.sort_values(
    "일일 관객수", ascending=False
).head(10).copy()

# Plotly의 범주형 색상 팔레트를 사용해 영화마다 다른 색 적용
color_palette = px.colors.qualitative.Bold

fig = px.bar(
    chart_df,
    x="표시용 영화명",
    y="일일 관객수",
    color="표시용 영화명",
    color_discrete_sequence=color_palette,
    text="일일 관객수",
    hover_data={
        "장르": True,
        "순위": True,
        "누적 관객수": ":,",
        "스크린 수": True,
        "표시용 영화명": False,
        "일일 관객수": ":,",
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
    texttemplate="%{text:,}명",
    textposition="outside",
    cliponaxis=False,
    marker_line_width=0,
    opacity=0.92,
)

fig.update_layout(
    height=490,
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
    margin=dict(l=20, r=25, t=70, b=100),
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


# --------------------------------------------------
# 전체 영화 정보 표
# --------------------------------------------------
st.markdown(
    '<div class="section-title">🎬 영화별 상세 정보</div>',
    unsafe_allow_html=True
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
    "※ 순위는 해당 날짜의 전체 박스오피스 순위입니다. "
    "장르 정보는 KOBIS 영화 상세정보 기준이며, "
    "등록되지 않았거나 조회되지 않는 정보는 '정보 없음'으로 표시됩니다. "
    "🏆 표시는 누적 관객수 100만 명 이상인 영화를 의미합니다."
)

st.markdown("""
<div class="footer">
    CINEMA BOX OFFICE · KOBIS OPEN API<br>
    영화진흥위원회 박스오피스 데이터를 활용한 영화 정보 대시보드
</div>
""", unsafe_allow_html=True)
