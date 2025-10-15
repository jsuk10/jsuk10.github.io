# scripts/pull_users.py
# 요구사항:
# 1) 월별 집계로 전환 (year-month), 최근 14개월은 API로 덮어쓰기, 그 이전은 기존 JSON 유지
# 2) total_users(병합된 월별 합) + today_users(금일 일일값) 기록

import os, json
import calendar
import datetime as dt
from pathlib import Path
from collections import defaultdict

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account

ASSET_PATH = Path("assets/users.json")

# ---------- 유틸 ----------
def months_ago(date: dt.date, months: int) -> dt.date:
    """date 기준 months개월 전 같은 '일'을 반환 (해당 월에 해당 일이 없으면 말일로 보정)"""
    y, m = date.year, date.month - months
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    d = min(date.day, last_day)
    return dt.date(y, m, d)

def ym_str(date: dt.date) -> str:
    return f"{date.year:04d}-{date.month:02d}"

def parse_existing_monthly(path: Path) -> dict:
    """
    기존 users.json에서 월별 데이터를 dict[YYYY-MM] = users 로 파싱.
    - 신규 스키마(monthly_series)가 있으면 그대로 읽어서 사용
    - 구 스키마(series: 일별)가 있으면 월별로 합산해 변환
    - 없으면 빈 dict 반환
    """
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    monthly = {}

    if isinstance(data, dict):
        # 1) 새로운 스키마: monthly_series
        if "monthly_series" in data and isinstance(data["monthly_series"], list):
            for item in data["monthly_series"]:
                ym = item.get("ym")
                users = int(item.get("users", 0) or 0)
                if isinstance(ym, str):
                    monthly[ym] = monthly.get(ym, 0) + users

        # 2) 예전 스키마: series (일별)
        elif "series" in data and isinstance(data["series"], list):
            temp = defaultdict(int)
            for item in data["series"]:
                # item: {"date": "YYYYMMDD", "users": N}
                dstr = str(item.get("date", ""))
                users = int(item.get("users", 0) or 0)
                if len(dstr) == 8 and dstr.isdigit():
                    ym = f"{dstr[0:4]}-{dstr[4:6]}"
                    temp[ym] += users
            monthly.update(temp)

    return monthly

# ---------- GA4 클라이언트 ----------
prop_id = os.environ["GA4_PROPERTY_ID"]
creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GA4_SA_JSON"]),
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
client = BetaAnalyticsDataClient(credentials=creds)

# ---------- 날짜 계산 ----------
today = dt.date.today()
# 월별 집계의 종료는 '어제'(부분월까지 누적). 금일은 별도(today_users)로 추출
end_date = today - dt.timedelta(days=1)
start_14m = months_ago(end_date, 14)

# ---------- 1) 최근 14개월 월별 데이터: API로 조회 ----------
# yearMonth 차원을 쓰면 월별 합계를 서버에서 바로 받을 수 있습니다.
monthly_req = RunReportRequest(
    property=f"properties/{prop_id}",
    dimensions=[Dimension(name="yearMonth")],  # 예: "202510"
    metrics=[Metric(name="activeUsers")],
    date_ranges=[DateRange(
        start_date=start_14m.isoformat(),
        end_date=end_date.isoformat()
    )]
)
monthly_resp = client.run_report(monthly_req)

monthly_api = {}
for r in monthly_resp.rows or []:
    ym_compact = r.dimension_values[0].value  # "YYYYMM"
    users = int(r.metric_values[0].value or 0)
    if len(ym_compact) == 6 and ym_compact.isdigit():
        ym = f"{ym_compact[0:4]}-{ym_compact[4:6]}"
        monthly_api[ym] = monthly_api.get(ym, 0) + users

# ---------- 2) 금일 방문자(today_users): 별도 단일 일자 조회 ----------
today_req = RunReportRequest(
    property=f"properties/{prop_id}",
    dimensions=[Dimension(name="date")],      # 일자 단위
    metrics=[Metric(name="activeUsers")],
    date_ranges=[DateRange(
        start_date=today.isoformat(),
        end_date=today.isoformat()
    )]
)
today_resp = client.run_report(today_req)
today_users = 0
if today_resp.rows:
    # rows는 1개(당일)만 있을 것
    today_users = int(today_resp.rows[0].metric_values[0].value or 0)

# ---------- 3) 기존 파일에서 14개월 이전 월은 유지 ----------
existing_monthly = parse_existing_monthly(ASSET_PATH)

merged = {}
# (a) 14개월 이전 월: 기존 파일에서 가져온 값 유지
# 기준: start_14m의 년월(YYYY-MM) 미만인 키
start_ym = ym_str(start_14m)

for ym, users in existing_monthly.items():
    if ym < start_ym:   # 문자열 비교로도 연-월은 안전하게 정렬됨(YYYY-MM 형식)
        merged[ym] = merged.get(ym, 0) + int(users)

# (b) 14개월 범위 내 월: API 결과로 덮어쓰기
for ym, users in monthly_api.items():
    merged[ym] = int(users)

# ---------- 4) total_users = 병합된 전 기간 월별 합 ----------
total_users = sum(int(v) for v in merged.values())

# ---------- 5) 출력 스키마 구성 ----------
# monthly_series: ym 오름차순으로 정렬
monthly_series = [
    {"ym": ym, "users": int(merged[ym])}
    for ym in sorted(merged.keys())
]

out = {
    "monthly_series": monthly_series,
    "total_users": int(total_users),          # 병합된 월별 합(고유 사용자 아님, 월별 activeUsers 합의 합)
    "today": today.isoformat(),
    "today_users": int(today_users),          # 금일 일일 activeUsers
    "generated_at": dt.datetime.utcnow().isoformat() + "Z"
}

# ---------- 6) 저장 ----------
os.makedirs(ASSET_PATH.parent, exist_ok=True)
with ASSET_PATH.open("w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Wrote {ASSET_PATH} (months={len(monthly_series)}, total={total_users}, today={today_users})")
