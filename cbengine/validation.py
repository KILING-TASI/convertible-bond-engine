"""Strict JSON and deterministic content digests."""
import hashlib
import json
import math
from pathlib import Path


def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('JSON出现重复字段：'+key)
        result[key]=value
    return result


def reject_constant(value):
    raise ValueError('JSON包含非有限数值：'+value)


def finite_float(token):
    value=float(token)
    if not math.isfinite(value): raise ValueError('JSON浮点数超出有限范围')
    return value


def loads(text):
    return json.loads(text,object_pairs_hook=unique_pairs,parse_constant=reject_constant,parse_float=finite_float)


def load(path):
    return loads(Path(path).read_text(encoding='utf-8-sig'))


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def digest(value): return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
