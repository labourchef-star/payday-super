"""Payday Super Due-Date Checker: free, no signup."""
import os, re, time, secrets, datetime as dt, html
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from . import engine as E, attribution as A
from .holidays import SRC, NAMES, FIRST, LAST
from .dbx import db
from .dbx_schema import SCHEMA
from .disposable import is_disposable
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
A.install(app,secure=os.environ.get("SECURE_COOKIES","1")=="1")
EVENTS=("visit","check_run","email_submit","pro_click")
with db() as c: c.executescript(SCHEMA); c.execute(A.DDL)
def today(): return dt.datetime.now(dt.timezone(dt.timedelta(hours=10))).date()
def bump(ev):
    d=today().isoformat()
    with db() as c:
        c.execute("insert into counters(day,event,n) values(?,?,1) on conflict(day,event) do update set n=counters.n+1",(d,ev)); A.bump(c,d,ev)
e=html.escape
CSS="""body{font:17px/1.5 system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;color:#1a1a1a}h1{font-size:1.5em;margin:.2em 0}
label{display:block;margin:.7em 0 .2em;font-weight:600}input,select,button{font:inherit;padding:10px;width:100%;box-sizing:border-box}
button{background:#0b5;color:#fff;border:0;border-radius:6px;margin-top:1em;font-weight:700}.box{border:2px solid #0b5;border-radius:8px;padding:12px;margin:1em 0}
.big{font-size:1.4em;font-weight:700}table{width:100%;border-collapse:collapse}td,th{padding:6px;border-bottom:1px solid #ddd;text-align:left}
.small{font-size:.85em;color:#555}.warn{background:#fff4d6;padding:8px;border-radius:6px}a{color:#05a}.cb{width:auto}"""
def page(title,body):
    return HTMLResponse(f"""<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="Work out when Payday Super is due for each pay run. 7 business days, weekends and state public holidays counted per ATO rules."><style>{CSS}</style><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230b5'/%3E%3Ctext x='16' y='23' font-size='20' font-family='Arial' font-weight='700' fill='white' text-anchor='middle'%3EK%3C/text%3E%3C/svg%3E"></head>
<body><p class="small"><a href="/">Payday Super due dates</a> · <a href="/sources">Sources</a> · <a href="/pro">Reminders Pro</a></p>{body}
<p class="small">Not tax advice. Dates follow the ATO's published Payday Super rules (linked on <a href="/sources">Sources</a>); check the ATO if your situation is unusual. Holiday data covers {FIRST.year}-{LAST.year}.</p>
<p class="small">Payday Super due dates is made by <a href="https://kerbform.com">Kerbform</a>. <a href="https://kerbform.com/privacy.html">Privacy</a> · <a href="https://kerbform.com/terms.html">Terms</a> · <a href="mailto:hello@kerbform.com">hello@kerbform.com</a></p></body></html>""")
FREQ={"weekly":7,"fortnightly":14,"monthly":0,"once":None}
def nxt(d,f):
    if f=="monthly":
        m=d.month%12+1; y=d.year+(d.month==12)
        import calendar; return dt.date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
    return d+dt.timedelta(days=FREQ[f])
def form(p="",f="fortnightly",first=False,ote=""):
    opts="".join(f'<option value="{k}"{" selected" if k==f else ""}>{k.capitalize() if k!="once" else "Just this payday"}</option>' for k in FREQ)
    return f"""<form action="/check" method="get"><label for="p">Payday (the date you pay wages)</label><input type="date" id="p" name="payday" required value="{e(p)}" min="{FIRST}" max="{LAST}">
<label for="f">How often you pay</label><select id="f" name="freq">{opts}</select>
<label for="o">Gross ordinary time earnings this pay, optional (A$)</label><input id="o" name="ote" inputmode="decimal" value="{e(ote)}" placeholder="e.g. 2400">
<label><input class="cb" type="checkbox" name="first" value="1"{" checked" if first else ""}> First payment to this employee's fund (new employee or new fund)</label>
<button>Show due date</button></form>"""
@app.get("/",response_class=HTMLResponse)
def home():
    bump("visit")
    return page("Payday Super due date checker",f"""<h1>When is Payday Super due?</h1>
<p>From 1 July 2026, super has to <b>reach the employee's fund</b> within 7 business days of payday. Weekends don't count, and nor does any day that's a public holiday across a whole state or territory, even one you're not in. Pick your payday and see the date.</p>{form(today().isoformat())}""")
@app.get("/check",response_class=HTMLResponse)
def check(payday:str="",freq:str="fortnightly",first:str="",ote:str=""):
    try: p=dt.date.fromisoformat(payday)
    except ValueError: return page("Check a date",'<p class="warn">Enter a payday date.</p>'+form())
    if freq not in FREQ: freq="once"
    o=None
    if ote.strip():
        try: o=float(re.sub(r"[,$\s]","",ote))
        except ValueError: o=None
    try:
        r=E.due(p,first=bool(first)); rows=[]; d=p
        for i in range(1 if freq=="once" else 6):
            if i: d=nxt(d,freq)
            try: rows.append(E.due(d))
            except E.OutOfRange: break
    except E.OutOfRange:
        return page("Out of range",f'<p class="warn">We only have public holiday data for {FIRST.year} to {LAST.year}.</p>'+form())
    bump("check_run")
    sk="".join(f"<li>{E.fmt(s['date'])}: {e(s['name'])} ({', '.join(s['states'])})</li>" for s in r["skipped"]) or "<li>None, only weekends.</li>"
    wn="".join(f'<p class="warn">{e(w)}</p>' for w in r["warnings"])
    amt=f"<p>Super at 12%: <b>A${E.sg(o):,.2f}</b> (12% of the earnings you entered; <a href='{E.ATO['about']}'>ATO</a>).</p>" if o else ""
    tbl="" if freq=="once" else "<h2>Your next pay runs</h2><table><tr><th>Payday</th><th>Send by</th><th>Fund must receive by</th></tr>"+"".join(f"<tr><td>{E.fmt(x['payday'])}</td><td>{E.fmt(x['send_by'])}</td><td><b>{E.fmt(x['due'])}</b></td></tr>" for x in rows)+"</table><p class='small'>Later paydays assume ordinary contributions (7 business days).</p>"
    return page(f"Payday Super due {E.fmt(r['due'])}",f"""<h1>Super for payday {E.fmt(p)}</h1>{wn}
<div class="box"><div>The fund must receive it by</div><div class="big">{E.fmt(r['due'])}</div>
<div>That's {r['business_days']} business days after payday (<a href="{E.ATO['deadlines']}">ATO payment deadlines</a>).</div>
<p>Suggested send-by date: <b>{E.fmt(r['send_by'])}</b>. This is our suggestion, not an ATO rule: it leaves {E.SEND_BUFFER} business days for your clearing house or fund to process the payment.</p></div>
{amt}<p>Public holidays skipped:</p><ul>{sk}</ul>
<p class="small">If it arrives late, the ATO can charge the super guarantee charge: the shortfall, plus notional earnings from {E.fmt(r['notional_earnings_start'])}, plus an administrative uplift that starts at 60% (<a href="{E.ATO['late']}">ATO</a>).</p>
{tbl}
<h2>Get a reminder before each send-by date</h2><form action="/remind" method="post"><input type="hidden" name="payday" value="{p}"><input type="hidden" name="freq" value="{e(freq)}">
<label for="em">Email</label><input id="em" type="email" name="email" required autocomplete="email">
<label><input class="cb" type="checkbox" name="consent" value="1" required> Email me Payday Super reminders. Unsubscribe any time.</label><button>Remind me</button></form>
<p><a href="/pro?from=result">Need reminders for every pay run and a record of when you paid? See Reminders Pro.</a></p>
<h2>Check another date</h2>{form(p.isoformat(),freq,bool(first),ote)}""")
EM=re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}$",re.I)
@app.post("/remind",response_class=HTMLResponse)
def remind(request:Request,email:str=Form(""),payday:str=Form(""),freq:str=Form("once"),consent:str=Form("")):
    email=email.strip().lower()
    if not EM.match(email) or not consent: return page("Check your email",'<p class="warn">Please enter a valid email and tick the box.</p><p><a href="/">Back</a></p>')
    if is_disposable(email): return page("Use a real email",'<p class="warn">Please use an email address you check.</p><p><a href="/">Back</a></p>')
    try: p=dt.date.fromisoformat(payday)
    except ValueError: p=None
    ip=(request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
    with db() as c:
        if c.execute("select count(*) n from hits where key=? and kind='remind' and ts>?",(ip,time.time()-3600)).fetchone()["n"]>=10: return page("Slow down",'<p class="warn">Too many requests. Try later.</p>')
        c.execute("insert into hits(key,kind,ts) values(?,?,?)",(ip,"remind",time.time()))
        ex=c.execute("select id from subscribers where email=?",(email,)).fetchone()
        if ex: c.execute("update subscribers set freq=?,next_payday=?,consent_ts=? where id=?",(freq,str(p or ""),time.time(),ex["id"])); sid=ex["id"]
        else:
            c.execute("insert into subscribers(email,state,freq,next_payday,consent_ts,ctok,utok,ip,created,expires) values(?,?,?,?,?,?,?,?,?,?)",
                (email,"",freq,str(p or ""),time.time(),secrets.token_urlsafe(16),secrets.token_urlsafe(16),ip,time.time(),(today()+dt.timedelta(days=28)).isoformat()))
            sid=c.execute("select id from subscribers where email=?",(email,)).fetchone()["id"]
        if p:
            try:
                r=E.due(p); c.execute("insert into reminders(sub_id,payday,due,send_by,remind_on) values(?,?,?,?,?)",(sid,str(p),str(r["due"]),str(r["send_by"]),str(E.sub_bd(r["send_by"],1))))
            except E.OutOfRange: pass
    bump("email_submit")
    return page("Saved",f"<h1>Saved</h1><p>We've saved {e(email)}. Free reminders cover your pay runs for the next 4 weeks.</p><p><a href='/'>Check another date</a></p>")
@app.get("/pro",response_class=HTMLResponse)
def pro(): 
    bump("pro_click")
    return page("Payday Super Reminders Pro","""<h1>Reminders Pro (coming soon)</h1><p>Planned: your pay schedule saved, an email before every send-by date, a log of the day you paid each run marked on time or late, and an export for your bookkeeper.</p>
<p>It isn't on sale yet. Leave your email on any result page and we'll tell you when it is.</p><p><a href="/">Back to the checker</a></p>""")
@app.get("/sources",response_class=HTMLResponse)
def sources():
    a="".join(f'<li><a href="{u}">{k}</a></li>' for k,u in E.ATO.items()); h="".join(f'<li><a href="{u}">{NAMES[k]}</a></li>' for k,u in SRC.items())
    return page("Sources",f"<h1>Sources</h1><h2>ATO Payday Super pages</h2><ul>{a}</ul><h2>State and territory public holidays</h2><ul>{h}</ul><p>Part-state holidays (like show days) are business days under the ATO rule, so we don't skip them.</p>")
@app.get("/privacy")
def privacy_redirect(): return RedirectResponse("https://kerbform.com/privacy.html",301)
@app.get("/terms")
def terms_redirect(): return RedirectResponse("https://kerbform.com/terms.html",301)
@app.get("/health")
def health(): return {"ok":True}
@app.get("/metrics")
def metrics(request:Request):
    if not os.environ.get("METRICS_TOKEN") or request.headers.get("authorization")!="Bearer "+os.environ["METRICS_TOKEN"]: return JSONResponse({"error":"unauthorised"},401)
    with db() as c:
        rows=[dict(r) for r in c.execute("select day,event,n from counters order by day").fetchall()]
        subs=c.execute("select count(*) n from subscribers").fetchone()["n"]; out={"counters":rows,"subscribers":subs}; out.update(A.report(c,EVENTS))
    return out
