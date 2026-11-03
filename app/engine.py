"""Payday Super due-date engine.
Rule (ATO, earnings paid from 1 July 2026): the contribution must be RECEIVED by the fund within 7 business days after payday
(20 business days for a new employee's / new fund's first contribution). Payday is day 0.
Business day = not Saturday/Sunday and not a public holiday for the whole of ANY Australian state or territory,
even if you're not in that state. Part-state holidays are business days."""
import datetime as dt, math
from .holidays import COUNTED, FIRST, LAST
SG_RATE=0.12
SEND_BUFFER=3   # guidance only: business days to allow for clearing house / fund processing
START=dt.date(2026,7,1)
ATO={
 "deadlines":"https://www.ato.gov.au/businesses-and-organisations/super-for-employers/payday-super/paying-super-on-payday/payment-deadlines-for-payday-super",
 "howto":"https://www.ato.gov.au/businesses-and-organisations/super-for-employers/paying-super-on-payday/how-to-work-out-and-pay-super",
 "changeover":"https://www.ato.gov.au/businesses-and-organisations/super-for-employers/payday-super-how-to-manage-super-during-the-changeover",
 "first_year":"https://www.ato.gov.au/businesses-and-organisations/super-for-employers/missed-or-late-payday-super-payments/getting-it-right-compliance-in-the-first-year-of-payday-super",
 "late":"https://www.ato.gov.au/businesses-and-organisations/super-for-employers/missed-or-late-payday-super-payments/what-happens-if-you-dont-pay-super-correctly",
 "about":"https://www.ato.gov.au/businesses-and-organisations/super-for-employers/about-payday-super",
}
class OutOfRange(ValueError): pass
def is_business_day(d):
    if not (FIRST<=d<=LAST): raise OutOfRange(f"Holiday data covers {FIRST.year}-{LAST.year} only")
    return d.weekday()<5 and d not in COUNTED
def add_bd(d,n):
    while n>0:
        d+=dt.timedelta(days=1)
        if is_business_day(d): n-=1
    return d
def sub_bd(d,n):
    while n>0:
        d-=dt.timedelta(days=1)
        if is_business_day(d): n-=1
    return d
def skipped(a,b):
    """Weekday holidays strictly after a up to b that were skipped, with the states that declared them."""
    out=[]; d=a+dt.timedelta(days=1)
    while d<=b:
        if d.weekday()<5 and d in COUNTED:
            hs=COUNTED[d]; out.append({"date":d,"name":hs[0]["name"],"states":sorted({h["state"] for h in hs})})
        d+=dt.timedelta(days=1)
    return out
def money(x): return math.floor(x*100+0.5)/100
def due(payday,first=False):
    """Returns dict with due (received-by) date, send_by guidance date, skipped holidays, warnings."""
    n=20 if first else 7
    d=add_bd(payday,n)
    sb=sub_bd(d,SEND_BUFFER)
    if sb<payday: sb=payday
    w=[]
    if payday<START: w.append("This payday is before 1 July 2026. Payday Super applies to earnings paid from 1 July 2026; earlier earnings follow the old quarterly due dates.")
    if payday.weekday()>=5: w.append("Payday falls on a weekend. The ATO counts payday as day 0, so the 7 business days start from the next business day.")
    return {"payday":payday,"business_days":n,"due":d,"send_by":sb,"skipped":skipped(payday,d),"warnings":w,
            "notional_earnings_start":d+dt.timedelta(days=1)}
def sg(ote):
    return money(max(0.0,ote)*SG_RATE)
def late_estimate(shortfall,days_late,gic_annual_pct=None):
    """ESTIMATE of the super guarantee charge (SGC) components per the ATO page:
    final shortfall + notional earnings (GIC rate, compounded daily, from the day after the due date)
    + administrative uplift (starts at 60% of shortfall + notional earnings; the ATO can reduce it, down to 0%)
    + choice loading (not estimated here). The GIC rate isn't hard-coded: the user enters the current rate from the ATO."""
    s=max(0.0,shortfall); days=max(0,int(days_late))
    ne=None
    if gic_annual_pct is not None and gic_annual_pct>=0 and days>0:
        ne=money(s*((1+gic_annual_pct/100/365)**days-1))
    base=s+(ne or 0.0)
    return {"shortfall":money(s),"days_late":days,"gic_pct":gic_annual_pct,"notional_earnings":ne,
            "uplift_max":money(base*0.60),"total_max":money(base*1.60),"uplift_min":0.0,"total_min":money(base)}
def fmt(d): return d.strftime("%a %-d %b %Y")
