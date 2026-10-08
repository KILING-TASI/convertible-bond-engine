"""Verify actual PDF bytes and explicitly scoped native-text checks, offline."""
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from .validation import file_digest, digest
from .engine import source


def compact(text): return re.sub(r'\s+','',text).replace('％','%')


def field_value(evidence,path):
    value=evidence
    for part in path.split('.'):
        value=value[int(part)] if isinstance(value,list) else value[part]
    return value


def verify_pdf(evidence,path):
    if not isinstance(evidence,dict): raise ValueError('PDF证据须为对象')
    filename=Path(path)
    if not filename.is_file() or filename.stat().st_size>100*1024*1024:
        raise ValueError('PDF不存在或超过100MiB')
    with filename.open('rb') as stream:
        if stream.read(5)!=b'%PDF-': raise ValueError('实际文件不是PDF')
    expected=evidence.get('document_sha256')
    if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):
        raise ValueError('需明确原PDF SHA256')
    actual=file_digest(filename)
    if actual!=expected: raise ValueError('实际PDF哈希与证据不符')
    parsed=urlparse(evidence.get('document_url',''))
    if parsed.scheme!='https' or parsed.hostname not in ('static.cninfo.com.cn','static.sse.com.cn') or parsed.username:
        raise ValueError('原文来源须为受支持的公开HTTPS域名')
    identity=evidence.get('document_identity')
    checks=evidence.get('verification_checks')
    if not isinstance(identity,dict) or not isinstance(checks,list) or not checks:
        raise ValueError('需明确document_identity及verification_checks')
    source(identity.get('issuer')); source(identity.get('title'))
    try: from pypdf import PdfReader
    except ImportError: raise ValueError('PDF核验需要可选依赖：pip install ".[evidence]"') from None
    try:
        reader=PdfReader(filename)
        front=''.join(compact(page.extract_text() or '') for page in reader.pages[:8])
        if any(compact(identity[key]) not in front for key in ('issuer','title')):
            raise ValueError('原PDF主体或标题不匹配')
        matched=[]; seen=set(); cache={}
        for check in checks:
            if not isinstance(check,dict): raise ValueError('核验项须为对象')
            name=check.get('field'); page=check.get('page'); excerpt=check.get('excerpt')
            if not isinstance(name,str) or not name or name in seen: raise ValueError('核验字段缺失或重复')
            seen.add(name)
            if type(page) is not int or not 1<=page<=len(reader.pages): raise ValueError('核验页码无效')
            source(excerpt)
            if page not in cache: cache[page]=compact(reader.pages[page-1].extract_text() or '')
            needle=compact(excerpt)
            if not needle or cache[page].count(needle)!=1: raise ValueError('原文摘录缺失或不唯一：'+name)
            expected_value=field_value(evidence,name)
            mode=check.get('mode')
            if mode=='number':
                token=check.get('number_token')
                source(token)
                if type(expected_value) not in (int,float) or not Decimal(str(expected_value)).is_finite():
                    raise ValueError('数字字段须为有限数值')
                if not re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?',token) or Decimal(token)!=Decimal(str(expected_value)):
                    raise ValueError('原文字面数值与字段不一致：'+name)
                if not re.search(r'(?<![0-9.])'+re.escape(token)+r'(?![0-9.])',needle):
                    raise ValueError('数字未出现在指定摘录：'+name)
            elif mode=='text':
                if not isinstance(expected_value,str) or compact(expected_value) not in needle:
                    raise ValueError('字段文本与指定摘录不一致：'+name)
            else: raise ValueError('核验方式仅支持number/text，布尔推论需保留人工解释')
            matched.append({'field':name,'page':page,'excerpt':excerpt,'value':expected_value,
                            'verification':'native-scoped-excerpt-'+mode})
    except ValueError: raise
    except (KeyError,IndexError,TypeError) as exc: raise ValueError('PDF核验字段绑定无效') from exc
    except Exception as exc: raise ValueError('PDF无法读取或提取原生文本；扫描件需人工复核') from exc
    # Bind result to every evidence field, including the declared semantic assumptions.
    payload={k:v for k,v in evidence.items() if k!='pdf_verification'}
    return {'status':'matched','document_sha256':actual,'evidence_sha256':digest(payload),
            'identity':identity,'fields':matched,'scope':'listed-native-text-checks-only',
            'limitations':['验证实际文件和指定原生文本，不验证来源下载真实性、完整条款或法律解释。',
                           '数值单位、含息判断和字段含义由核对底稿声明；匹配摘录不证明其他字段。']}
