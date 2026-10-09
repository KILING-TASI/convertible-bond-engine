"""Bounded issuer directory pagination evidence, never complete legal-event coverage."""
from datetime import datetime,timezone,timedelta,date
from urllib.parse import urlencode
from .validation import loads,digest,load
from .engine import iso_date,source
from .market import code_string
from .announcements import normalize_notices


def collect(spec,requester=None):
    issuer=code_string(spec['issuer_code']);code=code_string(spec['bond_code'])
    start=iso_date(spec['start']);end=iso_date(spec['end']);org=str(spec['org_id'])
    if not org.isascii() or not org.isdigit() or len(org)>20: raise ValueError('需明确数字组织ID及其来源')
    source(spec['identity_source'])
    if not 0<=(date.fromisoformat(end)-date.fromisoformat(start)).days<=366: raise ValueError('目录查询最多366日')
    if end>datetime.now(timezone(timedelta(hours=8))).date().isoformat(): raise ValueError('不能认证未来查询区间')
    if requester is None:
        try: import requests
        except ImportError: raise ValueError('显式联网目录审计需requests，可通过可选行情依赖安装') from None
        def requester(payload):
            r=requests.post('https://www.cninfo.com.cn/new/hisAnnouncement/query',data=payload,timeout=10)
            r.raise_for_status();return loads(r.text)
    payload={'pageNum':1,'pageSize':30,'column':'szse','tabName':'fulltext','plate':'','stock':issuer+','+org,
             'searchkey':'','secid':'','category':'','trade':'','seDate':start+'~'+end,'sortName':'','sortType':'','isHLtitle':'true'}
    pages=[];raw=[];errors=[];total=None;page=1
    while page<=20:
        try:
            response=requester(dict(payload,pageNum=page))
            reported=response['totalAnnouncement'];rows=response['announcements']
            if type(reported) is not int or reported<0 or not isinstance(rows,list): raise ValueError('分页字段结构异常')
            if total is None: total=reported
            if total!=reported: raise ValueError('分页期间总数变化，不能证明目录一致')
            if any(str(r.get('secCode',''))!=issuer for r in rows): raise ValueError('返回发行人身份冲突')
            if not rows and len(raw)<total: raise ValueError('尚未取得全部记录时出现空页')
            pages.append({'page':page,'returned_count':len(rows),'reported_total':reported,'response_sha256':digest(response),'response':response})
            raw+=rows
            if len(raw)>=total: break
            page+=1
        except Exception as exc:
            errors.append({'page':page,'category':type(exc).__name__,'message':'分页未完成或字段/身份冲突；不认证覆盖。'});break
    ids=[str(r.get('announcementId','')) for r in raw]
    observed=total is not None and len(raw)==total and len(ids)==len(set(ids)) and all(i.isdigit() for i in ids) and not errors
    if not observed and not errors: errors.append({'page':page,'category':'coverage_limit','message':'页数限制、数量或重复ID使覆盖未闭合。'})
    normalized=[]
    for r in raw:
        try:
            published=datetime.fromtimestamp(r['announcementTime']/1000,timezone(timedelta(hours=8))).date().isoformat()
            if not start<=published<=end: raise ValueError('公告日不在请求区间')
            url='https://www.cninfo.com.cn/new/disclosure/detail?'+urlencode({'stockCode':issuer,'announcementId':r['announcementId'],
                                                                           'orgId':org,'announcementTime':published})
            normalized.append({'代码':issuer,'公告标题':r['announcementTitle'],'公告时间':published,'公告链接':url})
        except (KeyError,TypeError,ValueError):
            observed=False;errors.append({'page':None,'category':'record_shape','message':'个别记录日期/标题异常。'})
    candidates=normalize_notices(normalized,issuer,code,spec['bond_name'],start,end)
    return {'type':'issuer-directory-coverage','method_version':'cninfo-pages-1.0','request':spec,
            'fetched_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'status':'pagination_observed' if observed else 'partial','pages':pages,'reported_total':total,
            'returned_records':len(raw),'errors':errors,'raw_records':raw,'bond_candidates':candidates,
            'legal_event_coverage':'unknown','conversion_history_complete':False,
            'limitations':['完整分页只针对所查询发行人、区间、目录返回记录；不认证全部条款事件或原文。',
                           '标题筛选可能遗漏调价、更正、承诺或发行人其他券；原文仍需逐条绑定。',
                           '查询快照不是首次公开时间证据；不据此填补交易日或停牌计数约定。']}


def attach(snapshot,audit):
    if not isinstance(audit,dict) or audit.get('type')!='issuer-directory-coverage': raise ValueError('目录审计类型无效')
    if audit['request']['bond_code']!=snapshot['code']: raise ValueError('目录审计转债代码冲突')
    mapped=snapshot.get('underlying_code')
    if mapped and audit['request']['issuer_code']!=mapped: raise ValueError('目录审计发行人映射冲突')
    combined=[]
    for n,page in enumerate(audit['pages'],1):
        response=page['response']
        if page['page']!=n or digest(response)!=page['response_sha256'] or len(response['announcements'])!=page['returned_count']:
            raise ValueError('分页次序、原始响应摘要或记录数不一致')
        if page['reported_total']!=response['totalAnnouncement'] or page['reported_total']!=audit['reported_total']:
            raise ValueError('分页总数与覆盖证据不一致')
        combined+=response['announcements']
    if digest(combined)!=digest(audit['raw_records']) or len(combined)!=audit['returned_records']:
        raise ValueError('目录原始记录与分页证据不一致')
    ids=[str(r.get('announcementId','')) for r in combined]
    if audit.get('legal_event_coverage')!='unknown' or audit.get('conversion_history_complete') is not False:
        raise ValueError('目录审计不能认证法律事件完整性')
    if audit['status']=='pagination_observed' and (audit['errors'] or len(combined)!=audit['reported_total'] or len(ids)!=len(set(ids)) or not all(i.isdigit() for i in ids)):
        raise ValueError('覆盖完成标签与分页事实不一致')
    from copy import deepcopy
    result=deepcopy(snapshot);result['directory_coverage']=deepcopy(audit)
    result['gaps'].append('已附查询区间和分页响应证据；只证明本次目录观察，不认证当前有效条款全覆盖。')
    return result


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        r=collect(load(a.input));a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        if r['status']!='pagination_observed':p.exit(3)
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
