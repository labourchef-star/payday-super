from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def test_home(): assert c.get("/").status_code==200
def test_check(): r=c.get("/check",params={"payday":"2026-07-10","freq":"fortnightly","ote":"2400"}); assert r.status_code==200 and "Tue 21 Jul 2026" in r.text and "288.00" in r.text
def test_check_bad(): assert "Enter a payday" in c.get("/check?payday=x").text
def test_out_of_range(): assert "only have public holiday" in c.get("/check?payday=2030-01-01").text
def test_remind_and_metrics():
    r=c.post("/remind",data={"email":"a@example.com","payday":"2026-07-10","freq":"weekly","consent":"1"}); assert "Saved" in r.text
    assert "real email" in c.post("/remind",data={"email":"a@mailinator.com","consent":"1"}).text
    c.get("/pro"); m=c.get("/metrics",headers={"authorization":"Bearer mtok"}).json(); assert m["subscribers"]==1
    ev={x["event"] for x in m["counters"]}; assert {"visit","check_run","email_submit","pro_click"}<=ev
def test_metrics_auth(): assert c.get("/metrics").status_code==401
def test_sources(): assert "ato.gov.au" in c.get("/sources").text
