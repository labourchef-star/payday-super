"""First-party campaign attribution (no third-party trackers).
On landing we store utm_source/utm_medium/utm_campaign/gclid in a first-party cookie ("src", 30 days, httponly).
Every funnel event is also counted under a source bucket:
  internal       - our own probes: ?internal=1, header X-Kerbform-Internal: 1, script/probe user agents, or a src cookie marked internal
  ads            - gclid present, or utm_medium cpc/ppc
  organic/other  - everything else
Request flags beat the cookie, and internal beats ads."""
import json, re, contextvars
from urllib.parse import quote, unquote
BUCKETS=("ads","organic/other","internal")
COOKIE="src"; MAX_AGE=30*86400
PROBE_UA=re.compile(r"curl|python|httpx|aiohttp|wget|go-http|libwww|node-fetch|axios|okhttp|headlesschrome|playwright|puppeteer|testclient|^$",re.I)
PAID_MEDIUM={"cpc","ppc","paid","paidsearch","paid_search"}
CUR=contextvars.ContextVar("kf_src_bucket",default="organic/other")
def _clip(v,n=100): return (v or "").strip()[:n]
def _load(raw):
    try: d=json.loads(unquote(raw or "")); return d if isinstance(d,dict) else {}
    except Exception: return {}
def _paid(d): return bool(d.get("gclid")) or (d.get("utm_medium","").lower() in PAID_MEDIUM)
def classify(q,headers,cookie_raw):
    """q, headers: mapping-like. Returns (bucket, new_cookie_dict_or_None)."""
    flag=str(q.get("internal","")).lower() in ("1","true","yes") or headers.get("x-kerbform-internal","")=="1"
    ua_probe=bool(PROBE_UA.search(headers.get("user-agent","")))
    land={k:_clip(q.get(k)) for k in ("utm_source","utm_medium","utm_campaign","gclid") if q.get(k)}
    new=None
    if land or flag:
        new=dict(land); 
        if flag: new["internal"]=1
    d=new if new is not None else _load(cookie_raw)
    if flag or ua_probe or d.get("internal"): b="internal"
    elif _paid(d): b="ads"
    else: b="organic/other"
    return b,new
def install(app,secure=True):
    @app.middleware("http")
    async def _attribution(req,call_next):
        b,new=classify(req.query_params,req.headers,req.cookies.get(COOKIE))
        tok=CUR.set(b)
        try: r=await call_next(req)
        finally: CUR.reset(tok)
        if new is not None: r.set_cookie(COOKIE,quote(json.dumps(new,separators=(",",":"))),max_age=MAX_AGE,httponly=True,samesite="lax",secure=secure)
        return r
def bucket(): return CUR.get()
DDL="create table if not exists counters_src(day text,event text,bucket text,n int default 0,primary key(day,event,bucket))"
def bump(c,day,ev):
    c.execute("insert into counters_src(day,event,bucket,n) values(?,?,?,1) on conflict(day,event,bucket) do update set n=counters_src.n+1",(day,ev,bucket()))
def report(c,events):
    rows=c.execute("select day,event,bucket,n from counters_src order by day").fetchall()
    days={}; tot={b:{e:0 for e in events} for b in BUCKETS}
    for r in rows:
        if r["bucket"] not in tot or r["event"] not in events: continue
        days.setdefault(r["day"],{b:{e:0 for e in events} for b in BUCKETS})[r["bucket"]][r["event"]]=r["n"]; tot[r["bucket"]][r["event"]]+=r["n"]
    return {"by_source":{"all_time":tot,"days":days,"since":rows[0]["day"] if rows else None,"note":"bucket counts start when attribution was deployed; legacy totals in all_time/days include earlier events"}}
