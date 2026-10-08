"""Append-only local snapshots and PDF blobs with integrity checks and writer lock."""
import os
import shutil
import re
from pathlib import Path
from datetime import datetime, timezone
from .validation import load, canonical, digest, file_digest
from .market import code_string


def signature(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):
        raise ValueError('归档摘要格式异常')
    return value


def bindings(snapshot):
    result=[]
    term=snapshot.get('issue_term_evidence',{})
    if term.get('pdf_verification'):
        result.append((term,term['pdf_verification']))
    for entry in snapshot.get('announcements',{}).get('entries',[]):
        if entry.get('pdf_verification'):
            result.append((entry['reviewed_evidence'],entry['pdf_verification']))
    for payload,binding in result:
        signature(binding['document_sha256'])
        clean={k:v for k,v in payload.items() if k!='pdf_verification'}
        if digest(clean)!=binding.get('evidence_sha256'):
            raise ValueError('PDF核验记录与当前证据字段不一致')
    return [binding for _,binding in result]


def verify_store(store,code):
    root=Path(store)/code_string(code)
    versions=root/'versions'
    records=[]; previous=None
    for index,path in enumerate(sorted(versions.glob('*.json')),1):
        record=load(path)
        version_hash=record.get('version_hash')
        body={k:v for k,v in record.items() if k!='version_hash'}
        if record.get('version')!=index or record.get('previous_hash')!=previous or digest(body)!=version_hash:
            raise ValueError('证据版本链不连续或内容摘要不一致')
        if record.get('code')!=code or digest(record['snapshot'])!=record['snapshot_hash']:
            raise ValueError('归档快照身份或摘要不一致')
        referenced=bindings(record['snapshot'])
        if any(b['document_sha256'] not in {d['sha256'] for d in record['documents']} for b in referenced):
            raise ValueError('版本记录缺少绑定的原文')
        for item in record.get('documents',[]):
            sig=signature(item['sha256'])
            blob=root/'blobs'/(sig+'.pdf')
            if not blob.is_file() or file_digest(blob)!=sig: raise ValueError('归档原文丢失或已修改')
        previous=version_hash; records.append(record)
    return records


def append(store,snapshot,documents=()):
    if not isinstance(snapshot,dict) or snapshot.get('kind')!='market_snapshot':
        raise ValueError('归档只支持市场快照')
    code=code_string(snapshot['code']); root=Path(store).resolve()/code
    root.mkdir(parents=True,exist_ok=True)
    lock=root/'write.lock'
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: raise ValueError('证据归档正在写入，请稍后重试') from None
    try:
        os.close(fd)
        records=verify_store(store,code)
        clean={k:v for k,v in snapshot.items() if k!='archive_receipt'}
        snap_hash=digest(clean)
        blobs=root/'blobs'; blobs.mkdir(exist_ok=True)
        registered={signature(d['sha256']) for d in documents}
        # Verification labels in a stored snapshot must have actual bound bytes.
        references=bindings(clean)
        for binding in references:
            sig=binding['document_sha256']
            existing=blobs/(sig+'.pdf')
            if sig not in registered and (not existing.is_file() or file_digest(existing)!=sig):
                raise ValueError('归档核验记录缺少对应实际PDF')
        files=[]
        for document in documents:
            p=Path(document['path']); sig=document['sha256']
            if file_digest(p)!=sig: raise ValueError('原文在核验后发生变化')
            target=blobs/(sig+'.pdf')
            if target.exists():
                if file_digest(target)!=sig: raise ValueError('原文归档摘要不一致')
            else:
                pending=blobs/(sig+'.pending')
                try:
                    shutil.copyfile(p,pending)
                    if file_digest(pending)!=sig: raise ValueError('原文复制校验失败')
                    os.replace(pending,target)
                finally:
                    if pending.exists(): pending.unlink()
            files.append({'sha256':sig,'bytes':target.stat().st_size})
        # Include already archived PDFs referenced by preserved verifications.
        for binding in references:
            sig=binding['document_sha256']
            if sig not in {d['sha256'] for d in files}:
                files.append({'sha256':sig,'bytes':(blobs/(sig+'.pdf')).stat().st_size})
        if records and records[-1]['snapshot_hash']==snap_hash and records[-1]['documents']==files:
            r=records[-1]
            return {'status':'unchanged','code':code,'version':r['version'],'version_hash':r['version_hash']}
        body={'schema_version':1,'code':code,'version':len(records)+1,
              'previous_hash':records[-1]['version_hash'] if records else None,
              'recorded_at':datetime.now(timezone.utc).isoformat(),
              'snapshot_hash':snap_hash,'snapshot':clean,'documents':files}
        record_hash=digest(body)
        versions=root/'versions'; versions.mkdir(exist_ok=True)
        path=versions/(f'{body["version"]:06d}-{record_hash[:12]}.json')
        pending=path.with_suffix('.pending')
        try:
            with pending.open('xb') as stream: stream.write(canonical(dict(body,version_hash=record_hash)))
            if path.exists(): raise ValueError('版本文件已存在，拒绝覆盖')
            os.replace(pending,path)
        finally:
            if pending.exists(): pending.unlink()
        return {'status':'appended','code':code,'version':body['version'],'version_hash':record_hash}
    finally: lock.unlink(missing_ok=True)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description='离线检查证据版本链与归档PDF摘要')
    parser.add_argument('store'); parser.add_argument('--code',required=True)
    args=parser.parse_args()
    try:
        records=verify_store(args.store,args.code)
        if not records: raise ValueError('没有可核对的版本记录')
        print(json.dumps({'status':'stored-content-verified','code':args.code,'versions':len(records),
                          'latest_hash':records[-1]['version_hash'],
                          'note':'内容完整性检查，不认证来源真实、完整法律解释或不可篡改。'},ensure_ascii=False))
    except (ValueError,KeyError,TypeError,OSError) as exc: parser.exit(2,str(exc)+'\n')
