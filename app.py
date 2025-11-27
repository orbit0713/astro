import streamlit as st
from datetime import datetime
import random
import math
from zoneinfo import ZoneInfo
import os
from starplot import ZenithPlot, Observer, Star, _


# ==========================================
# 세팅
# ==========================================


# 성도 최대 표시 등급
MAX_PLOT_MAG = 4.0


# 이미지 저장할 폴더 만들기
os.makedirs("charts", exist_ok=True)




# ==========================================
# RA/DEC -> ALT 변환 함수
# ==========================================


def calc_alt_deg(star, obs: Observer) -> float:
    lat_rad = math.radians(obs.lat)
    dec_rad = math.radians(star.dec)


    lst_deg = obs.lst
    ha_deg = (lst_deg - star.ra) % 360
    ha_rad = math.radians(ha_deg)


    sin_alt = (
        math.sin(lat_rad) * math.sin(dec_rad)
        + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
    )
    sin_alt = max(-1, min(1, sin_alt))


    return math.degrees(math.asin(sin_alt))




# ==========================================
# Streamlit UI
# ==========================================


st.set_page_config(page_title="Missing Star Generator", layout="wide")
st.title("⭐ 미싱 스타 성도 생성기 (Streamlit)")


st.write("날짜/시간, 위치, 밝기 등급을 선택하면 자동으로 문제/정답 성도를 만들어줍니다.")


# 입력 UI
col1, col2 = st.columns(2)


with col1:
    date_input = st.date_input("날짜 선택")
    time_input = st.time_input("시간 선택", value=datetime.now().time())


with col2:
    lat = st.number_input("위도 입력", value=37.5665, format="%.6f")
    lon = st.number_input("경도 입력", value=126.9780, format="%.6f")


n = st.number_input("삭제 후보 최대 등급 n", value=3.0, min_value=0.0, max_value=MAX_PLOT_MAG, step=0.1)
k = st.number_input("삭제할 별 수 k", value=10, min_value=1, step=1)




# 생성 버튼
run_btn = st.button("👉 성도 생성하기")


if run_btn:


    # ==========================================
    # 시간 조합
    # ==========================================


    dt = datetime.combine(date_input, time_input).replace(
        tzinfo=ZoneInfo("Asia/Seoul")
    )


    # 관측자 설정
    observer = Observer(
        dt=dt,
        lat=lat,
        lon=lon,
    )


    # ==========================================
    # 후보 별 선정 (지평선 위 + n등급 이하)
    # ==========================================


    candidate_pre = Star.find(
        where=[
            _.magnitude <= MAX_PLOT_MAG,
            _.magnitude <= n,
            _.hip.notnull(),
        ]
    )


    candidate_stars = []
    for s in candidate_pre:
        alt = calc_alt_deg(s, observer)
        if alt > 0:
            candidate_stars.append(s)


    if len(candidate_stars) < k:
        st.error(
            f"지평선 위의 삭제 후보 별이 {len(candidate_stars)}개인데 k={k}개를 요청했습니다."
        )
        st.stop()


    # 실제 삭제 별 선정
    missing_stars = random.sample(candidate_stars, k)
    missing_hip_ids = {s.hip for s in missing_stars}


    # ==========================================
    # 1) 문제 성도
    # ==========================================


    problem_plot = ZenithPlot(observer=observer, resolution=3000, scale=0.9)


    hip_list = ",".join(str(h) for h in missing_hip_ids)
    problem_sql = (
        f"select * from _ "
        f"where magnitude <= {MAX_PLOT_MAG} "
        f"and (hip is null or hip not in ({hip_list}))"
    )


    problem_plot.stars(sql=problem_sql, where_labels=[False])
    problem_plot.horizon()


    problem_path = "/tmp/problem.png"
    problem_plot.export(problem_path, transparent=True)


    # ==========================================
    # 2) 정답 성도
    # ==========================================


    answer_plot = ZenithPlot(observer=observer, resolution=3000, scale=0.9)
    answer_plot.constellations()


    answer_plot.stars(where=[_.magnitude <= MAX_PLOT_MAG], where_labels=[False])


    answer_plot.stars(
        where=[_.hip.isin(list(missing_hip_ids))],
        where_labels=[False],
        style__marker__color="red",
        style__marker__size=18,
    )


    answer_plot.horizon()


    answer_path = "/tmp/answer.png"
    answer_plot.export(answer_path, transparent=True)


    # ==========================================
    # 출력
    # ==========================================


    st.success("성도 생성 완료!")


    colA, colB = st.columns(2)


    with colA:
        st.subheader("문제 성도")
        st.image(problem_path)


    with colB:
        st.subheader("정답 성도")
        st.image(answer_path)


    st.subheader("삭제된 별 목록 (HIP / 등급)")
    st.write(
        [
            f"HIP {s.hip} | mag={s.magnitude:.2f}"
            for s in missing_stars
        ]
    )