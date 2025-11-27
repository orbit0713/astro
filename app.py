import streamlit as st
from datetime import datetime
import random
import os
from zoneinfo import ZoneInfo

from starplot import ZenithPlot, Observer, Star


# =========================================================
# Render-friendly 설정
# =========================================================
TMP_DIR = "/tmp"   # Render 서버에서 파일 저장 가능한 유일한 경로
MAX_PLOT_MAG = 4.0


# =========================================================
# 별 데이터를 안전 모드로 로드 (DuckDB 사용 안 함)
# =========================================================
@st.cache_data
def load_stars_safe():
    """
    starplot이 내부적으로 DuckDB를 사용하는데,
    Render는 DuckDB extension을 불러올 수 없어서 실패한다.
    따라서 Star.find() 대신 내부 DataFrame을 직접 접근하는 안전 모드 사용.
    """
    df = Star._table.to_pandas()   # starplot이 가진 전체 별 데이터 로드
    df = df[df["magnitude"] <= MAX_PLOT_MAG]  # 4등급 이하만 미리 필터
    df = df[df["hip"].notnull()]              # HIP 없는 별 제거
    return df


# =========================================================
# Streamlit UI
# =========================================================
st.title("⭐ 성도에서 별 지우기 문제 생성기 (Render 버전)")

col1, col2 = st.columns(2)
with col1:
    date_str = st.text_input("관측 날짜 (YYYY-MM-DD)", "2023-07-13")
with col2:
    time_str = st.text_input("관측 시간 (HH:MM)", "22:00")

col3, col4 = st.columns(2)
with col3:
    lat = st.number_input("위도", value=37.5665)
with col4:
    lon = st.number_input("경도", value=126.9780)

col5, col6 = st.columns(2)
with col5:
    n = st.number_input("삭제 후보 최대 등급 n", value=3.0, step=0.1)
with col6:
    k = st.number_input("삭제할 별 개수 k", value=5, step=1)

go = st.button("성도 생성하기")


# =========================================================
# 실행 로직
# =========================================================
if go:

    st.info("성도 생성 중… 잠시만 기다려 주세요.")

    # 1) datetime 처리
    try:
        dt = datetime.fromisoformat(f"{date_str} {time_str}")
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    except:
        st.error("날짜 또는 시간 형식이 잘못되었습니다.")
        st.stop()

    # 2) Observer 설정
    observer = Observer(
        dt=dt,
        lat=lat,
        lon=lon,
    )

    # 3) starplot 데이터 안전모드 불러오기
    df = load_stars_safe()

    # 4) 고도 계산 후 지평선 위 별만 추리기
    tmp_plot = ZenithPlot(observer=observer, resolution=1500)
    alts = []

    for idx, row in df.iterrows():
        alt, az = tmp_plot.altaz(row["ra"], row["dec"])
        alts.append(alt)

    df["alt"] = alts
    df_visible = df[df["alt"] > 0]  # 지평선 위 별

    # 삭제 후보
    df_cand = df_visible[df_visible["magnitude"] <= n]

    if len(df_cand) < k:
        st.error(f"지울 수 있는 별이 부족합니다. (후보 {len(df_cand)}개)")
        st.stop()

    # 지울 별 선택
    missing_stars = df_cand.sample(k)
    missing_hips = set(missing_stars["hip"])

    # =========================================================
    # 5) 성도 생성 — 문제용
    # =========================================================
    problem_plot = ZenithPlot(observer=observer, resolution=1500, scale=0.85)

    # HIP 제거된 상태로 그림
    df_problem = df_visible[~df_visible["hip"].isin(missing_hips)]

    # starplot stars() 대신 safe mode 사용
    for _, row in df_problem.iterrows():
        problem_plot._draw_star(row["ra"], row["dec"], row["magnitude"])

    problem_plot.horizon()

    problem_path = os.path.join(TMP_DIR, "problem.png")
    problem_plot.export(problem_path, transparent=True)

    # =========================================================
    # 6) 성도 생성 — 정답용
    # =========================================================
    answer_plot = ZenithPlot(observer=observer, resolution=1500, scale=0.85)
    answer_plot.constellations()

    # 전체 별 그림
    for _, row in df_visible.iterrows():
        answer_plot._draw_star(row["ra"], row["dec"], row["magnitude"])

    # 삭제된 별만 빨간색
    for _, row in missing_stars.iterrows():
        answer_plot._draw_star(
            row["ra"], row["dec"], row["magnitude"],
            style=dict(marker=dict(color="red", size=14))
        )

    answer_plot.horizon()

    answer_path = os.path.join(TMP_DIR, "answer.png")
    answer_plot.export(answer_path, transparent=True)

    # =========================================================
    # 7) 출력
    # =========================================================
    st.success("성도 생성 완료!")

    colA, colB = st.columns(2)

    with colA:
        st.subheader("문제 성도")
        st.image(problem_path)

    with colB:
        st.subheader("정답 성도")
        st.image(answer_path)

    st.subheader("삭제된 별 목록 (HIP / 등급)")
    st.write([f"HIP {hip} | mag={df[df.hip == hip]['magnitude'].values[0]:.2f}"
              for hip in missing_hips])
📌 requirements.txt (Render용 최종 버전)
이렇게 GitHub에 업로드하자:

makefile
코드 복사
streamlit==1.31.0
starplot==0.4.1
numpy
pandas
skyfield
