"""Small CLI scenario index reusing existing examples; no new pricing model."""
import argparse,copy,hashlib,html,json,os,subprocess,sys
from pathlib import Path
from importlib.metadata import version,PackageNotFoundError
from .validation import load,digest


def run(examples,out):
    if out.exists():raise ValueError('scenario output directory exists; choose a new directory')
    # Read all required existing teaching fixtures before creating output.
    bridge=load(examples/'bridge-fixed-demo.json');flat=load(examples/'crosscheck-flat.json')
    nonflat=load(examples/'crosscheck-nonflat.json');snapshot=load(examples/'analysis-market-demo.json')
    out.mkdir(parents=True,exist_ok=False);cases=[]
    try:software_version=version('convertible-bond-engine')
    except PackageNotFoundError:software_version='0.12.3'
    def execute(name,spec,module,expected,check,error=None,analysis=None):
        folder=out/name;folder.mkdir();input_file=folder/'input.json'
        input_file.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        target=folder/'native'
        args=[sys.executable,'-m',module,str(input_file)]
        if module=='cbengine.bridge':args+=['--out-dir',str(target)]
        else:args+=['--out',str(folder/'actual.json')]
        if analysis is not None:
            path=folder/'analysis.json';path.write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            args+=['--analysis-input',str(path),'--quality-as-of','2026-10-09']
        env=dict(os.environ,PYTHONIOENCODING='utf-8')
        proc=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=env,timeout=30)
        actual_file=target/'result.json' if module=='cbengine.bridge' else folder/'actual.json'
        actual=load(actual_file) if actual_file.exists() else None
        assert proc.returncode==(2 if error else 0),(name,proc.stderr)
        if error:
            assert error in proc.stderr,(name,proc.stderr)
            assert actual is None,name
        else:check(actual)
        receipt={'case':name,'is_demo':True,'expected':expected,'actual':actual,'returncode':proc.returncode,
                 'error':proc.stderr or None,'input_sha256':digest(spec),'command':args[1:],
                 'software_version':software_version,'scenario_method_version':'cli-scenario-acceptance-1',
                 'method_version':actual.get('method_version','evidence-clause-1') if actual else 'validation-only',
                 'input_file':'input.json','analysis_file':'analysis.json' if analysis is not None else None,
                 'analysis_sha256':digest(analysis) if analysis is not None else None,
                 'status':'passed','scope':'teaching CLI/JSON; not real source or investment validation'}
        (folder/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');cases.append(receipt)
        return actual,folder
    def close(value,expected):assert abs(value-expected)<1e-9,(value,expected)
    one=copy.deepcopy(bridge);one.update(price=98,accrued_interest=2,source='教学一年现金流，独立手算锚点',discount_curve=[[.01,.04],[2,.04]])
    one['cashflows']=[{'date':'2027-10-09','coupon':5,'redemption':100,'coupon_tax':1,'redemption_tax':0,'source':'教学显式税额'}]
    one['maturity_payment'].update(quoted_amount=105)
    def one_check(r):
        close(r['dirty_price'],100);close(r['bond_present_value'],105/1.04);close(r['yield_gross'],.05);close(r['yield_net'],.04)
        assert r['clean_price']==98 and all(v=='unknown' for v in r['current_rights'].values())
    first,folder=execute('clean-one-year',one,'cbengine.bridge',{'basis':'hand arithmetic: 105/1.04; 105/100-1; 104/100-1','dirty_price':100,'gross_yield':.05,'net_yield':.04,'rights':'unknown'},one_check)
    frozen=hashlib.sha256((folder/'native/result.json').read_bytes()).hexdigest()
    repeated=subprocess.run([sys.executable,'-m','cbengine.bridge',str(folder/'input.json'),'--out-dir',str(folder/'native')],capture_output=True,text=True)
    assert repeated.returncode==2 and hashlib.sha256((folder/'native/result.json').read_bytes()).hexdigest()==frozen
    (folder/'repeat-output.json').write_text(json.dumps({'expected_exit':2,'actual_exit':repeated.returncode,'old_result_sha256':frozen,'unchanged':True}),encoding='utf-8')
    dirty=copy.deepcopy(one);dirty.update(price_basis='dirty',price=100)
    execute('dirty-equivalent',dirty,'cbengine.bridge',{'basis':'clean+AI=dirty equivalence'},lambda r:close(r['yield_net'],first['yield_net']))
    unknown=copy.deepcopy(dirty);unknown.pop('accrued_interest');unknown.pop('accrued_interest_source')
    def unknown_accrual_check(r):
        assert r['clean_price'] is None and r['accrued_interest'] is None
    execute('dirty-accrual-unknown',unknown,'cbengine.bridge',{'clean_price':None,'accrued_interest':None},unknown_accrual_check)
    bad=copy.deepcopy(one);bad.pop('accrued_interest');bad.pop('accrued_interest_source')
    execute('clean-missing-accrual',bad,'cbengine.bridge',{'error':'clean price requires explicit accrued interest'},None,'clean price requires explicit accrued interest')
    bad=copy.deepcopy(one);bad['cashflows'][-1]['redemption']=105
    execute('double-final-coupon',bad,'cbengine.bridge',{'error':'maturity amount conflicts'},None,'maturity amount conflicts')
    execute('nonflat-nodes',nonflat,'cbengine.crosscheck',{'basis':'historical matched QuantLib1.43 node-aligned benchmark; not executed here','pv':93.37334315172102},lambda r: (close(r['engine']['dirty_price'],93.37334315172102),close(r['engine']['zero_curve_parallel_duration'],3.784982084553996)))
    boundary=copy.deepcopy(flat);boundary['cashflows'].insert(0,{'date':flat['as_of'],'gross_payment':2})
    values={}
    for name,day,include in [('before','2026-10-08',False),('include','2026-10-09',True),('exclude','2026-10-09',False),('after','2026-10-10',False)]:
        s=copy.deepcopy(boundary);s['as_of']=s['settlement_date']=day;s['include_settlement_date_flows']=include
        if name=='after':s['cashflows']=s['cashflows'][1:]
        r,_=execute('payment-'+name,s,'cbengine.crosscheck',{'basis':'payment-boundary cash conservation and one-day roll; tested jointly'},lambda r:None)
        values[name]=r['engine']
    factor=(1+flat['rate'])**(1/365)
    close(values['include']['dirty_price']-values['exclude']['dirty_price'],2)
    close(values['include']['dv01'],values['exclude']['dv01'])
    close(values['before']['dirty_price'],values['include']['dirty_price']/factor)
    close(values['after']['dirty_price'],values['exclude']['dirty_price']*factor)
    (out/'payment-invariants.json').write_text(json.dumps({'status':'passed','identities':['include-exclude=2','same-day cash DV01=0','before=include/one-day-factor','after=exclude*one-day-factor'],'values':values},indent=2),encoding='utf-8')
    evidence={'code':'DEMO','as_of':'2026-10-09','stock_price_basis':'unadjusted','observation_source':'教学未复权价格','calendar_source':'教学两日列表','calendar_complete':True,'conversion_history_source':'教学调价列表，非完整公告链','conversion_history_complete':False,
        'trading_days':['2026-10-08','2026-10-09'],'observations':[{'date':'2026-10-08','stock_price':12},{'date':'2026-10-09','stock_price':12}],
        'conversion_history':[{'effective_on':'2026-01-01','price':10,'source':'教学'},{'effective_on':'2026-10-09','price':8,'source':'教学'}],
        'clauses':{'call':{'source':'教学','window':2,'count':1,'ratio':1.3,'direction':'above','inclusive':True,'rolling':True,'active_from':'2026-01-01','active_until':'2027-01-01','reset_on':[]}}}
    def clause_check(r):
        state=r['independent_analysis']['clauses']['states']['call']
        assert state['count']==1 and state['conditional_observed_result'] is True
        assert state['trigger_condition_met'] is None and state['status']=='unknown'
        assert all(v=='unknown' for v in r['event_chain']['current_state'].values())
    execute('condition-met-rights-unknown',snapshot,'cbengine.cli',{'basis':'12<10*1.3 on day1;12>=8*1.3 on day2; 1/1 condition met, no announcement','count':1,'current_rights':'unknown'},clause_check,analysis=evidence)
    bad=copy.deepcopy(evidence);bad['observations'].pop()
    execute('missing-trading-day',snapshot,'cbengine.cli',{'error':'所提供交易日不完整匹配'},None,'所提供交易日不完整匹配',bad)
    # Existing renderer, actual report generated from the same successful JSON; no new UI/model.
    clause=out/'condition-met-rights-unknown'
    r=subprocess.run([sys.executable,'-m','cbengine.cli',str(clause/'actual.json'),'--format','html','--quality-as-of','2026-10-09','--out',str(clause/'report.html')],capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert r.returncode==0,r.stderr
    summary={'method_version':'cli-scenario-acceptance-1','status':'passed','is_demo':True,'cases':[{'case':r['case'],'status':r['status'],'expected':r['expected'],'method_version':r['method_version']} for r in cases],
      'coverage':'12 representative CLI cases plus duplicate-output and joint payment invariants; no new pricing algorithm',
      'not_covered':['real-data legal completeness','live data','full optional component matrix','option/LSM/probability models','new visual acceptance']}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=''.join('<tr><td>'+html.escape(x['case'])+'</td><td>通过（教学）</td><td><a href="'+html.escape(x['case'])+'/receipt.json">输入关联、预期与实际</a></td></tr>' for x in cases)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>教学情景验收</title><h1>教学情景验收 · 非真实覆盖</h1><p>静态已跑CLI结果，不重新定价；未知保持未知。</p><table>'+rows+'</table><p><a href="condition-met-rights-unknown/report.html">条款缺证据实际资料卡</a></p><p><a href="summary.json">方法版本和未覆盖范围</a></p>',encoding='utf-8')
    return summary


def run_cn(examples,out):
    if out.exists():raise ValueError('scenario output directory exists; choose a new directory')
    base=load(examples/'bridge-fixed-demo.json');snapshot=load(examples/'analysis-market-demo.json')
    out.mkdir(parents=True,exist_ok=False);cases=[]
    try:software_version=version('convertible-bond-engine')
    except PackageNotFoundError:software_version='0.12.3'
    def call(name,spec,module,expected,check=None,error=None,analysis=None):
        folder=out/name;folder.mkdir();input_file=folder/'input.json'
        input_file.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        args=[sys.executable,'-m',module,str(input_file)]
        actual_file=folder/'native/result.json' if module=='cbengine.bridge' else folder/'actual.json'
        args+=['--out-dir',str(folder/'native')] if module=='cbengine.bridge' else ['--out',str(actual_file)]
        if analysis is not None:
            f=folder/'analysis.json';f.write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            args+=['--analysis-input',str(f),'--quality-as-of','2026-06-08']
        r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'),timeout=30)
        assert r.returncode==(2 if error else 0),(name,r.stderr)
        actual=load(actual_file) if actual_file.exists() else None
        if error:assert error in r.stderr and actual is None,(name,r.stderr)
        else:check(actual)
        receipt={'case':name,'is_demo':True,'input_file':'input.json','analysis_file':'analysis.json' if analysis else None,
            'input_sha256':digest(spec),'analysis_sha256':digest(analysis) if analysis else None,
            'expected':expected,'actual':actual,'returncode':r.returncode,'error':r.stderr or None,'status':'passed',
            'software_version':software_version,'method_version':'cn-scenario-acceptance-1','scope':'selected official facts plus synthetic prices/calendar; no live coverage'}
        (folder/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        cases.append(receipt)
        if actual and module=='cbengine.cli':
            render=subprocess.run([sys.executable,'-m','cbengine.cli',str(actual_file),'--format','html','--quality-as-of','2026-06-08','--out',str(folder/'report.html')],capture_output=True,text=True,encoding='utf-8',timeout=30)
            assert render.returncode==0,render.stderr
    unit=copy.deepcopy(base);unit.update(price_basis='dirty',price=118.5,trading_quantity=10,conversion_shares=119)
    call('quantity-unit-not-supported',unit,'cbengine.bridge',{'basis':'SSE2025 arts5/6/13 plus issuer prospectus p20: quote price/face trading amount/conversion shares different','expected':'reject operational quantity fields, not silently price as another unit'},error='unsupported bridge fields')
    snapshot=copy.deepcopy(snapshot);snapshot.update(quote_time='2026-06-08',fetched_at='2026-06-08T00:00:00+08:00',name='CN教学窗口：非真实市场价格')
    evidence={'code':'DEMO','as_of':'2026-06-08','stock_price_basis':'unadjusted','observation_source':'教学10.86元/股，不是实际行情',
      'calendar_source':'教学仅列两日，不认证完整沪市日历','calendar_complete':False,'conversion_history_source':'借公告所选8.57/8.35字段演示，不还原完整历史','conversion_history_complete':False,
      'trading_days':['2026-06-05','2026-06-08'],'observations':[{'date':'2026-06-05','stock_price':10.86},{'date':'2026-06-08','stock_price':10.86}],
      'conversion_history':[{'effective_on':'2026-06-05','price':8.57,'source':'教学窗口起始延用原文旧价；不声明真实首次生效日'}, {'effective_on':'2026-06-08','price':8.35,'source':'公告2026-06-02原文字面实施日与新价，未认证全部更正'}],
      'clauses':{'call':{'source':'上银原募集说明书窗口参考，未确认当前有效承诺/重置；教学观察','window':30,'count':15,'ratio':1.3,'direction':'above','inclusive':True,'rolling':True,'active_from':'2021-07-29','active_until':'2027-01-24','reset_on':[]}}}
    def history_check(r):
        c=r['independent_analysis']['clauses'];state=c['states']['call']
        assert [o['conversion_price'] for o in c['observations']]==[8.57,8.35]
        assert state['count']==1 and state['status']=='unknown' and state['trigger_condition_met'] is None
        assert all(v=='unknown' for v in r['event_chain']['current_state'].values())
    call('effective-price-window',snapshot,'cbengine.cli',{'basis':'10.86 < 8.57*1.3=11.141;10.86 >= 8.35*1.3=10.855; no current-price backfill','count':1,'formal_rights':'unknown'},history_check,analysis=evidence)
    halted=copy.deepcopy(evidence);halted['halted_days']=[{'date':'2026-06-05','source':'教学假设交易停牌，不是该公告的暂停转股','reason':'实际计数政策未核实'}];halted['observations']=halted['observations'][1:]
    def halted_check(r):
        s=r['independent_analysis']['clauses']['states']['call']
        assert s['count'] is None and s['status']=='unknown' and s['evidence_status']=='halt-count-policy-unverified'
    call('halt-count-unknown',snapshot,'cbengine.cli',{'count':None,'basis':'unknown trading halt count policy; do not silently delete/fill day'},halted_check,analysis=halted)
    conflicting=copy.deepcopy(halted);conflicting['observations']=copy.deepcopy(evidence['observations'])
    call('halt-with-quote-conflict',snapshot,'cbengine.cli',{'basis':'declared trading halt cannot carry tradable close; conversion suspension is a different event'},error='已声明停牌日不能同时提供',analysis=conflicting)
    fee=copy.deepcopy(base);fee.update(fees=3,cash_arrival_date='2030-10-10')
    call('fee-arrival-not-supported',fee,'cbengine.bridge',{'basis':'issuer prospectus p20 distinguishes interest obligation/payment window and holder tax; not guessed arrival or uniform tax/fees','expected':'unsupported operational fields rejected'},error='unsupported bridge fields')
    summary={'method_version':'cn-scenario-acceptance-1','status':'passed','is_demo':True,'groups':4,'cli_cases':5,
      'cases':[{'case':c['case'],'status':c['status'],'expected':c['expected']} for c in cases],
      'official_basis':'selected SSE2025 articles5/6/13 and historical113042 announcement/prospectus fields; not global rule defaults',
      'not_covered':['real calendar/halt policy','actual cash arrival/tax/fees','current legal rights','order/conversion execution','live market/visual/option models']}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=''.join('<li><a href="'+c['case']+'/receipt.json">'+html.escape(c['case'])+'</a>：教学通过</li>' for c in cases)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>CN转债情景：教学与官方所选字段分开</h1><p>报价/现金流按每100面值，单位人民币；时间为输入日期或教学北京时间，不是真实可得时刻。</p><ul>'+rows+'</ul><a href="effective-price-window/report.html">调价窗口资料卡</a><p><a href="summary.json">范围与未覆盖</a></p>',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cn-only',action='store_true');p.add_argument('--example-dir',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args()
    try:r=(run_cn if a.cn_only else run)(a.example_dir.resolve(),a.out_dir.resolve());print(json.dumps({'status':r['status'],'cases':len(r['cases'])}))
    except (ValueError,OSError,AssertionError,subprocess.TimeoutExpired) as e:p.exit(2,str(e)+'\n')
