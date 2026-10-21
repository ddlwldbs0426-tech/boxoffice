
import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일별 박스오피스 · 한국 시간 기준")

# 2. 한국 시간 기준으로 어제 날짜 계산
KST = ZoneInfo("Asia/Seoul")
yesterday = datetime.now(KST).date() - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")


# 3. API에서 받은 숫자 문자열을 정수로 변환하는 함수
def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# 4. JSON 응답을 우선 처리하고, XML 응답도 확인하는 함수
def parse_response(response):
    try:
        return response.json(), None
    except ValueError:
        pass

    try:
        root = ET.fromstring(response.text)
        result = {}

        # 인증키 오류 등 API 오류 정보 확인
        fault = root.find(".//faultInfo")
        if fault is not None:
            result["faultInfo"] = {
                child.tag: child.text for child in list(fault)
            }

        # XML 형식의 영화 목록 확인
        box_result = root.find(".//boxOfficeResult")
        if box_result is not None:
            items = []
            for movie in box_result.findall(".//dailyBoxOffice"):
                items.append({
                    child.tag: child.text
                    for child in list(movie)
                })
            result["boxOfficeResult"] = {
                "dailyBoxOfficeList": items
            }

        if result:
            return result, None

        return None, "응답을 JSON 또는 예상한 XML 형식으로 해석하지 못했습니다."

    except ET.ParseError:
        return None, "서버 응답이 JSON/XML 형식이 아닙니다."


# 5. 인증키는 코드에 직접 쓰지 않고 Secrets에서 가져오기
try:
    api_key = st.secrets["KOBIS_KEY"]
except Exception:
    st.error(
        "인증키를 찾을 수 없습니다. Streamlit Cloud의 "
        "앱 설정에서 Settings → Secrets를 확인해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_인증키"', language="toml")
    st.stop()

if not str(api_key).strip():
    st.error(
        "KOBIS_KEY가 비어 있습니다. Secrets에 올바른 인증키를 입력해 주세요."
    )
    st.stop()


# 6. KOBIS 일별 박스오피스 API 요청
api_url = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

params = {
    "key": str(api_key).strip(),
    "targetDt": target_dt
}

with st.spinner("박스오피스 데이터를 불러오는 중입니다..."):
    try:
        response = requests.get(
            api_url,
            params=params,
            timeout=20
        )
    except requests.exceptions.Timeout:
        st.error("API 요청 시간이 초과되었습니다.")
        st.info(
            "잠시 후 다시 실행하거나 인터넷 연결 및 "
            "KOBIS 서버 상태를 확인해 주세요."
        )
        st.stop()

    except requests.exceptions.RequestException as exc:
        st.error("API 서버에 연결하지 못했습니다.")
        st.info(
            "인터넷 연결, API 주소 또는 서버 상태를 확인해 주세요."
        )
        st.caption(f"세부 정보: {exc}")
        st.stop()


# 7. HTTP 상태 코드 확인
if response.status_code != 200:
    st.error(
        f"API 요청 실패: HTTP 상태 코드 {response.status_code}"
    )
    st.info(
        "API 주소, 네트워크 연결 및 KOBIS 서버 상태를 확인해 주세요."
    )
    st.stop()


# 8. 응답 내용 해석
data, parse_error = parse_response(response)

if parse_error:
    st.error("API 응답을 읽지 못했습니다.")
    st.info(
        f"{parse_error} API 주소와 서버 응답 형식을 확인해 주세요."
    )
    st.stop()


# 9. 상태 코드가 200이어도 API 자체 오류가 있는지 확인
fault_info = data.get("faultInfo") if isinstance(data, dict) else None

if fault_info:
    fault_code = fault_info.get("errorCode", "알 수 없음")
    fault_message = fault_info.get(
        "message",
        "오류 메시지가 제공되지 않았습니다."
    )

    st.error("KOBIS API에서 오류를 반환했습니다.")
    st.write(f"오류 코드: {fault_code}")
    st.write(f"오류 내용: {fault_message}")
    st.info(
        "인증키가 정확한지, API 이용 신청 및 이용 상태에 "
        "문제가 없는지 확인해 주세요."
    )
    st.stop()


# 10. 박스오피스 결과와 영화 목록 확인
box_result = (
    data.get("boxOfficeResult")
    if isinstance(data, dict)
    else None
)

if not isinstance(box_result, dict):
    st.error("응답에 boxOfficeResult가 없습니다.")
    st.info(
        "KOBIS API 요청 주소와 응답 형식을 확인해 주세요."
    )
    st.stop()

movie_list = box_result.get("dailyBoxOfficeList", [])

if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning(
        f"{yesterday.strftime('%Y년 %m월 %d일')}의 영화 목록이 비어 있습니다."
    )
    st.info(
        "해당 날짜의 집계 자료가 아직 제공되지 않았거나 "
        "데이터가 없을 수 있습니다. 조회 날짜와 KOBIS "
        "서비스 상태를 확인한 뒤 다시 시도해 주세요."
    )
    st.stop()


# 11. 영화 정보를 정리하고 문자열 숫자를 정수로 변환
movies = []

for item in movie_list:
    movies.append({
        "순위": to_int(item.get("rank")),
        "영화명": item.get("movieNm") or "영화명 없음",
        "개봉일": item.get("openDt") or "-",
        "관객수": to_int(item.get("audiCnt")),
        "누적관객": to_int(item.get("audiAcc")),
        "스크린수": to_int(item.get("scrnCnt")),
        "상영횟수": to_int(item.get("showCnt")),
        "순위 증감": to_int(item.get("rankInten"))
    })

movies.sort(key=lambda movie: movie["순위"])

top_movie = movies[0]


# 12. 조회 날짜와 1위 영화의 지표 카드 표시
st.subheader(
    f"📅 {yesterday.strftime('%Y년 %m월 %d일')} 박스오피스"
)

st.caption(
    "관객수는 해당 날짜의 관객 수이며, "
    "누적관객은 개봉 이후 누적 관객 수입니다."
)

st.markdown(f"### 🏆 1위: {top_movie['영화명']}")

card1, card2, card3 = st.columns(3)

card1.metric(
    "일일 관객수",
    f"{top_movie['관객수']:,}명"
)

card2.metric(
    "누적 관객수",
    f"{top_movie['누적관객']:,}명"
)

card3.metric(
    "스크린 수",
    f"{top_movie['스크린수']:,}개"
)


# 13. 전체 영화 순위를 표로 표시
st.subheader("전체 순위")

display_rows = []

for movie in movies:
    display_rows.append({
        "순위": movie["순위"],
        "영화명": movie["영화명"],
        "개봉일": movie["개봉일"],
        "관객수": f"{movie['관객수']:,}",
        "누적관객": f"{movie['누적관객']:,}",
        "스크린수": f"{movie['스크린수']:,}"
    })

st.dataframe(
    display_rows,
    use_container_width=True,
    hide_index=True
)


# 14. 관객수 기준 상위 5편을 막대그래프로 표시
st.subheader("📊 관객수 상위 5편")

top_five = sorted(
    movies,
    key=lambda movie: movie["관객수"],
    reverse=True
)[:5]

chart_rows = [
    {
        "영화명": movie["영화명"],
        "관객수": movie["관객수"]
    }
    for movie in top_five
]

st.bar_chart(
    chart_rows,
    x="영화명",
    y="관객수",
    horizontal=True
)


# 15. 자료 출처와 조회 기준일 표시
st.caption(
    "자료: 영화진흥위원회(KOBIS) 일별 박스오피스 Open API"
)
st.caption(f"조회 기준일: {target_dt}")
