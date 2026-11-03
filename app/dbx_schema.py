from .dbx import ID
SCHEMA=f"""
create table if not exists subscribers(id {ID},email text unique,state text,freq text,next_payday text,consent_ts double precision,confirmed int default 0,ctok text,utok text,ip text,created double precision,expires text);
create table if not exists reminders(id {ID},sub_id int,payday text,due text,send_by text,remind_on text,status text default 'pending',sent_ts double precision);
create table if not exists hits(key text,kind text,ts double precision);
create table if not exists counters(day text,event text,n int default 0,primary key(day,event));
create table if not exists kv(k text primary key,v text);
create index if not exists hits_k on hits(key,kind,ts);
create index if not exists rem_on on reminders(status,remind_on)
"""
