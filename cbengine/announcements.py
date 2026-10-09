"""Issuer announcement discovery. Titles identify candidates, never legal states."""
import html
import re
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
from .engine import iso_date, source, finite
from .market import code_string, fetch_rows


def title_categories(title):
    categories=[]
    no_reset=any(x in title for x in ('不下修','不向下修正','不提出向下修正'))
    if no_reset: categories.append('no_reset_candidate')
    elif '下修' in title or '向下修正' in title: categories.append('reset_candidate')
    if any(x in title for x in ('不提前赎回','不赎回','不行使赎回','不强赎')):
        categories.append('no_call_candidate')
    elif '赎回' in title or '强赎' in title:
        categories.append('redemption_candidate')
    if not no_reset and '转股' in title and any(x in title for x in ('价格','价调整','下修','向下修正')):
        categories.append('conversion_price_candidate')
    if '停止转股' in title or '暂停转股' in title:
        categories.append('conversion_suspension_candidate')
    if '回售' in title: categories.append('put_candidate')
    if '付息' in title or '兑付' in title: categories.append('payment_candidate')
    if '评级' in title: categories.append('rating_candidate')
    if '转股结果' in title: categories.append('conversion_result_candidate')
    return categories or ['other_bond_candidate']


def normalize_notices(rows,issuer,bond_code,bond_name,start,end):
    issuer=code_string(issuer); bond_code=code_string(bond_code)
    iso_date(start); iso_date(end)
    if not isinstance(rows,list): raise ValueError('公告返回结构异常')
    entries={}; discarded=0
    for row in rows:
        if not isinstance(row,dict): raise ValueError('公告记录必须是对象')
        if str(row.get('代码','')).strip()!=issuer:
            discarded+=1; continue
        title=html.unescape(re.sub(r'<[^>]*>','',str(row.get('公告标题') or ''))).strip()
        exact=bool(bond_code in title or (bond_name and bond_name!=bond_code and bond_name in title))
        related=exact or any(x in title for x in ('可转债','可转换公司债','转债','转股'))
        if not related: continue
        try:
            published=datetime.fromisoformat(str(row.get('公告时间'))).date().isoformat()
        except (TypeError,ValueError):
            discarded+=1; continue
        if not start <= published <= end:
            discarded+=1; continue
        url=str(row.get('公告链接') or '')
        parsed=urlparse(url)
        if parsed.scheme not in ('http','https') or parsed.hostname not in ('www.cninfo.com.cn','cninfo.com.cn'):
            discarded+=1; continue
        url=url.replace('http://','https://',1)
        entry={'title':title,'published_on':published,'source_url':url,
               'issuer_code':issuer,'bond_identity':'title_match' if exact else 'issuer_candidate',
               'categories':title_categories(title),'body_reviewed':False,
               'effective_date':None,'changes_applied':False}
        if url in entries and entries[url]!=entry:
            raise ValueError('同一公告链接出现冲突内容，拒绝生成时间线')
        entries[url]=entry
    return {'status':'discovered','source':'巨潮资讯发行人公告查询','issuer_code':issuer,
            'query_start':start,'query_end':end,'query_category':'全部',
            'returned_rows':len(rows),'discarded_rows':discarded,
            'entries':sorted(entries.values(),key=lambda r:(r['published_on'],r['source_url']),reverse=True),
            'coverage':'仅查询区间内、标题含转债相关词的发行人公告；不保证全部债券事件覆盖。',
            'note':'公告日不等于生效日；标题匹配不证明属于该转债；正文未核对，不改变引擎输入或当前条款状态。'}


def discover(snapshot,start=None,end=None,issuer=None,fetcher=fetch_rows):
    if not isinstance(snapshot,dict) or snapshot.get('kind')!='market_snapshot' or snapshot.get('status')=='failed':
        raise ValueError('公告查询需要已取得的市场快照')
    today=datetime.fromisoformat(snapshot['fetched_at']).date()
    end=iso_date(end or today.isoformat())
    start=iso_date(start or (date.fromisoformat(end)-timedelta(days=180)).isoformat())
    if not 0 <= (date.fromisoformat(end)-date.fromisoformat(start)).days <= 366:
        raise ValueError('公告查询区间须在0至366日内')
    if date.fromisoformat(end)>today: raise ValueError('查询结束日不得晚于快照获取日')
    mapped=snapshot.get('underlying_code')
    if issuer and mapped and issuer!=mapped:
        raise ValueError('指定发行人代码与行情映射冲突')
    issuer=code_string(issuer or mapped or '')
    result=dict(snapshot)
    result['sources']=dict(snapshot['sources'],announcements='https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search')
    try:
        rows=fetcher(f'notices:{issuer}:{start.replace("-","")}:{end.replace("-","")}')
        result['announcements']=normalize_notices(rows,issuer,snapshot['code'],snapshot['name'],start,end)
    except ValueError as exc:
        result['announcements']={'status':'failed','issuer_code':issuer,'query_start':start,'query_end':end,
                                 'entries':[],'errors':[str(exc)],'coverage':'查询失败，不能推断无公告或无风险。'}
    result['gaps']=snapshot['gaps']+['后续公告仅为发现结果；全文、适用标的、生效日及执行条件尚未核对。',
        '公告查询以获取日为截止，可能晚于历史行情日；不能作为该行情日的回测信息集。公告元数据不能证明当日具体公开时刻。']
    return result


def attach_reviews(snapshot,reviews):
    """Caller-supplied evidence declarations, not automated legal verification."""
    if not isinstance(snapshot,dict) or snapshot.get('kind')!='market_snapshot':
        raise ValueError('正文核对底稿需要市场快照')
    notices=snapshot.get('announcements')
    if not notices or notices['status']!='discovered':
        raise ValueError('正文核对底稿需要成功取得的公告候选列表')
    if not isinstance(reviews,list) or not reviews: raise ValueError('公告核对底稿必须为非空列表')
    entries={n['source_url']:dict(n) for n in notices['entries']}
    used=set()
    for review in reviews:
        if not isinstance(review,dict) or review.get('bond_code')!=snapshot['code']:
            raise ValueError('正文底稿必须确认同一转债代码')
        url=review.get('announcement_url')
        if url not in entries or url in used:
            raise ValueError('正文底稿必须唯一对应已发现的公告链接')
        used.add(url)
        source(review.get('review_method')); source(review.get('document_url'))
        parsed=urlparse(review['document_url'])
        if parsed.scheme!='https' or parsed.hostname!='static.cninfo.com.cn':
            raise ValueError('本版正文底稿需要巨潮静态原文来源')
        iso_date(review['reviewed_on'])
        if review.get('published_on')!=entries[url]['published_on']:
            raise ValueError('正文底稿公告日与元数据冲突')
        effective=review.get('effective_on')
        if effective is not None: iso_date(effective)
        if review.get('event_type') not in ('conversion_price_adjustment','payment','redemption','no_call','reset','no_reset','rating','put','other'):
            raise ValueError('未知正文事件类型')
        facts=dict(review.get('facts',{}))
        if review['event_type']=='conversion_price_adjustment':
            if effective is None: raise ValueError('转股价调整底稿需要明确生效日')
            facts['old_conversion_price']=finite(facts['old_conversion_price'],'old conversion price',True)
            facts['new_conversion_price']=finite(facts['new_conversion_price'],'new conversion price',True)
        entry=entries[url]
        entry.update(body_reviewed=True,review_basis='caller_supplied_evidence',
                     effective_date=effective,reviewed_evidence=dict(review,facts=facts))
    result=dict(snapshot)
    result['announcements']=dict(notices,entries=[entries[n['source_url']] for n in notices['entries']])
    result['gaps']=snapshot['gaps']+['正文核对标记依据所附底稿；不证明其他公告已核对，不自动变更转股价、承诺期限或条款计数。']
    return result
