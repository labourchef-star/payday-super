import datetime as dt, pytest
from app import engine as E
D=dt.date
def due(y,m,d,**k): return E.due(D(y,m,d),**k)["due"]
# ATO worked examples (sources/ato_payday_super_rules_20261103.md)
def test_ato_example_wages_10_jul_2026(): assert due(2026,7,10)==D(2026,7,21)   # part-state NT show day 17 Jul is a business day
def test_ato_example_changeover_6_jul_2026(): assert due(2026,7,6)==D(2026,7,15)
def test_ato_example_nt_picnic_day_counts_for_everyone(): assert due(2026,7,30)==D(2026,8,11)   # state-specific (NT-only) whole-territory holiday
def test_ato_example_first_contribution_20bd(): assert due(2026,7,9,first=True)==D(2026,8,7)
def test_ato_example5_2028(): r=E.due(D(2028,1,4)); assert r["due"]==D(2028,1,13) and r["notional_earnings_start"]==D(2028,1,14)
def test_weekends_only():
    # Mon 14 Sep 2026 -> no holidays -> Wed 23 Sep
    assert due(2026,9,14)==D(2026,9,23)
def test_easter_2027():
    # Thu 25 Mar 2027: Good Fri 26, Easter Mon 29 Mar skipped -> 26..: Tue30(1) Wed31(2) Thu1(3) Fri2(4) Mon5(5) Tue6(6) Wed7(7)
    r=E.due(D(2027,3,25)); assert r["due"]==D(2027,4,7)
    assert [s["date"] for s in r["skipped"]]==[D(2027,3,26),D(2027,3,29)]
def test_state_specific_wa_day_and_canberra_day():
    # Fri 29 May 2026: Mon 1 Jun (WA Day + ACT Reconciliation) and Mon 8 Jun (King's Birthday most states) skipped
    r=E.due(D(2026,5,29)); assert r["due"]==D(2026,6,11)
    assert {"WA","ACT"}<=set(r["skipped"][0]["states"])
def test_vic_afl_friday_2026_and_wa_kings_birthday():
    # Thu 24 Sep 2026: Fri 25 (VIC AFL) + Mon 28 (WA King's) skipped -> Tue29(1)..Mon5 Oct is Labour Day NSW/SA/ACT + QLD King's -> skip
    assert due(2026,9,24)==D(2026,10,8)
def test_payday_on_weekend():
    r=E.due(D(2026,8,15))   # Saturday
    assert r["due"]==D(2026,8,25) and any("weekend" in w for w in r["warnings"])
def test_year_boundary_christmas_2026():
    # Thu 24 Dec 2026 (part-day eve is a business day): skip 25, 28 Dec, 1 Jan
    r=E.due(D(2026,12,24)); assert r["due"]==D(2027,1,7)
    assert [s["date"] for s in r["skipped"]]==[D(2026,12,25),D(2026,12,28),D(2027,1,1)]
def test_year_boundary_2027_2028():
    # Fri 24 Dec 2027: skip Mon 27, Tue 28 Dec, Mon 3 Jan 2028 -> Wed29(1) Thu30 Fri31(3) Tue4(4) Wed5 Thu6 Fri7(7)
    assert due(2027,12,24)==D(2028,1,7)
def test_part_state_and_local_holidays_not_counted():
    # Mon 2 Nov 2026: Tas Recreation Day (part) and Melbourne Cup Tue 3 Nov (local substitution) treated as business days
    assert due(2026,11,2)==D(2026,11,11)
def test_send_by_is_3_business_days_earlier():
    r=E.due(D(2026,7,30)); assert r["send_by"]==D(2026,8,6)
def test_pre_july_warning(): assert any("1 July 2026" in w for w in E.due(D(2026,6,15))["warnings"])
def test_out_of_range():
    with pytest.raises(E.OutOfRange): E.due(D(2028,12,28))
def test_sg_and_late_estimate():
    assert E.sg(2500)==300.0 and E.sg(1234.56)==148.15
    e=E.late_estimate(300,30); assert e["notional_earnings"] is None and e["uplift_max"]==180.0 and e["total_max"]==480.0
    e=E.late_estimate(1000,365,10.0); assert 105<e["notional_earnings"]<106 and e["total_max"]==pytest.approx((1000+e["notional_earnings"])*1.6,abs=0.02)
