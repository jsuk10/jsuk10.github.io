# scripts/pull_users.py
import os, json, datetime as dt
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account

prop_id = os.environ["GA4_PROPERTY_ID"]
creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GA4_SA_JSON"]),
    scopes=["https://www.googleapis.com/auth/analytics.readonly"]
)
client = BetaAnalyticsDataClient(credentials=creds)

today = dt.date.today()
start = (today - dt.timedelta(days=7)).isoformat()
end   = (today - dt.timedelta(days=1)).isoformat()

req = RunReportRequest(
    property=f"properties/{prop_id}",
    dimensions=[Dimension(name="date")],
    metrics=[Metric(name="activeUsers")],
    date_ranges=[DateRange(start_date=start, end_date=end)]
)
resp = client.run_report(req)

series = []
total_users = 0
for r in resp.rows:
    d = r.dimension_values[0].value   # yyyymmdd
    u = int(r.metric_values[0].value or 0)
    series.append({"date": d, "users": u})
    total_users += u

out = {
    "range": {"start": start, "end": end},
    "total_users": total_users,           # 최근 7일 합계
    "series": series,                     # 필요 없으면 지워도 됨
    "generated_at": dt.datetime.utcnow().isoformat() + "Z"
}

os.makedirs("assets", exist_ok=True)
with open("assets/users.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Wrote assets/users.json")
