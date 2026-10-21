
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 어제의 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일별 박스오피스 API")

# ==========================================
# 2. 한국 시간 기준으로 어제 날짜 계산
# ==========================================
try:
    korea_today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    yesterday = korea_today - timedelta(days=1)
    target_dt = yesterday.strftime("%Y%m%d")
    display_date = yesterday.strftime("%Y년 %m월 %d일")
except Exception as e:
    st.error(f"날짜 계산 오류: {type(e).__name__}")
    st.stop()

st.write(f"**조회 기준일:** {display_date}")

# ==========================================
# 3. Secrets에서 인증키 읽기
# ==========================================
try:
    api_key = str(st.secrets["KOBIS_KEY"]).strip()
    if not api_key:
        raise ValueError("인증키가 비어 있습니다.")
except Exception:
    st.error(
        "인증키를 읽을 수 없습니다. Streamlit Cloud의 "
        "앱 설정 → Secrets에 다음 내용을 등록해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_인증키"', language="toml")
    st.info("인증키를 코드나 공개 GitHub 저장소에 입력하지 마세요.")
    st.stop()

# ==========================================
# 4. KOBIS API 요청 함수
# ==========================================
API_URL = (
    "https://kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

@st.cache_data(ttl=1800, show_spinner=False)
def get_box_office(api_key_value, date_value):
    """API를 요청하고 영화 목록을 반환합니다."""
    response = requests.get(
        API_URL,
        params={
            "key": api_key_value,
            "targetDt": date_value,
        },
        timeout=(5, 20),
    )

    response.raise_for_status()

    try:
        data = response.json()
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError("API 응답이 JSON 형식이 아닙니다.") from e

    if not isinstance(data, dict):
        raise ValueError("API 응답 구조가 올바르지 않습니다.")

    # HTTP 상태 코드가 200이어도 API 오류일 수 있습니다.
    if "faultInfo" in data:
        fault = data.get("faultInfo") or {}
        if not isinstance(fault, dict):
            fault = {}

        code = fault.get("errorCode", "확인 불가")
        message = fault.get("message", "오류 메시지가 없습니다.")

        raise RuntimeError(
            f"KOBIS API 오류 ({code}): {message}"
        )

    box_result = data.get("boxOfficeResult")

    if not isinstance(box_result, dict):
        raise ValueError(
            "응답에 boxOfficeResult가 없습니다."
        )

    movies = box_result.get("dailyBoxOfficeList")

    if not isinstance(movies, list):
        raise ValueError(
            "dailyBoxOfficeList가 목록 형식이 아닙니다."
        )

    return movies


# ==========================================
# 5. API 요청 및 오류 처리
# ==========================================
with st.spinner("박스오피스 정보를 불러오는 중입니다..."):
    try:
        movie_list = get_box_office(api_key, target_dt)

    except requests.exceptions.Timeout:
        st.error("KOBIS 서버 응답 시간이 초과되었습니다.")
        st.info("잠시 후 다시 시도해 주세요.")
        st.stop()

    except requests.exceptions.HTTPError as e:
        status = (
            e.response.status_code
            if e.response is not None
            else "확인 불가"
        )
        st.error(f"KOBIS 서버 HTTP 오류: {status}")
        st.info("API 주소와 서버 상태를 확인해 주세요.")
        st.stop()

    except requests.exceptions.ConnectionError:
        st.error("KOBIS 서버에 연결하지 못했습니다.")
        st.info("네트워크 연결 또는 KOBIS 서버 상태를 확인해 주세요.")
        st.stop()

    except requests.exceptions.RequestException as e:
        st.error(f"API 통신 오류: {type(e).__name__}")
        st.info("잠시 후 다시 시도해 주세요.")
        st.stop()

    except RuntimeError as e:
        st.error(str(e))
        st.info(
            "Secrets의 KOBIS_KEY가 정확한지, "
            "인증키가 정상적으로 발급되었는지 확인해 주세요."
        )
        st.stop()

    except ValueError as e:
        st.error(str(e))
        st.info("KOBIS API 응답 구조를 확인해 주세요.")
        st.stop()

    except Exception as e:
        st.error(f"예상하지 못한 오류: {type(e).__name__}")
        st.info(
            "Streamlit Cloud의 Manage app → Logs에서 "
            "자세한 오류 내용을 확인해 주세요."
        )
        st.stop()

# ==========================================
# 6. 영화 목록이 비어 있는 경우
# ==========================================
if len(movie_list) == 0:
    st.warning(
        f"{display_date}의 박스오피스 목록이 비어 있습니다."
    )
    st.info(
        "해당 날짜의 집계 자료가 아직 제공되지 않았거나 "
        "API가 빈 목록을 반환했을 수 있습니다. "
        "조회 날짜와 KOBIS 홈페이지의 자료를 확인해 주세요."
    )
    st.stop()

# ==========================================
# 7. 데이터 정리
# ==========================================
df = pd.DataFrame(movie_list)

required_columns = [
    "rank",
    "movieNm",
    "openDt",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    st.error(
        "API 응답에서 필요한 항목이 누락되었습니다: "
        + ", ".join(missing)
    )
    st.info("KOBIS API 응답 형식을 확인해 주세요.")
    st.stop()

# API 숫자는 문자열로 오므로 숫자형으로 변환합니다.
numeric_columns = [
    "rank",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col], errors="coerce"
    )

df = df.dropna(
    subset=["rank", "audiCnt"]
).copy()

if df.empty:
    st.error("순위나 관객 수를 숫자로 읽을 수 없습니다.")
    st.stop()

for col in numeric_columns:
    df[col] = df[col].fillna(0).astype(int)

df["movieNm"] = (
    df["movieNm"]
    .fillna("영화명 정보 없음")
    .astype(str)
)

df["openDt"] = df["openDt"].fillna("").astype(str)

df = df.sort_values("rank").reset_index(drop=True)

# ==========================================
# 8. 1위 영화 지표 카드 세 장
# ==========================================
first = df.iloc[0]

st.subheader("🏆 일별 박스오피스 1위")
st.markdown(f"### {first['movieNm']}")

card1, card2, card3 = st.columns(3)

card1.metric(
    "일일 관객 수",
    f"{first['audiCnt']:,}명",
)

card2.metric(
    "누적 관객 수",
    f"{first['audiAcc']:,}명",
)

card3.metric(
    "스크린 수",
    f"{first['scrnCnt']:,}개",
)

# ==========================================
# 9. 전체 영화 순위 표
# ==========================================
st.subheader("📋 전체 박스오피스 순위")

table = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]
].copy()

table.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수",
]

table["개봉일"] = table["개봉일"].replace(
    "", "정보 없음"
)

for col in ["관객수", "누적관객", "스크린수"]:
    table[col] = table[col].map(
        lambda value: f"{value:,}"
    )

table["순위"] = table["순위"].astype(int).astype(str)

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)

# ==========================================
# 10. 관객 수 상위 5편 막대그래프
# ==========================================
st.subheader("📊 관객 수 상위 5편")

top5 = (
    df.nlargest(5, "audiCnt")
    .sort_values("audiCnt", ascending=True)
)

chart = top5.set_index("movieNm")[["audiCnt"]]
chart = chart.rename(columns={"audiCnt": "관객 수"})

st.bar_chart(
    chart,
    use_container_width=True,
)

# ==========================================
# 11. 자료 안내 및 새로고침
# ==========================================
st.caption(
    "자료: 영화진흥위원회(KOBIS) 일별 박스오피스 API"
)

if st.button("🔄 최신 자료 다시 불러오기"):
    st.cache_data.clear()
    st.rerun()
