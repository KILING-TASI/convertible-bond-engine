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
    except PackageNotFoundError:software_version='0.11.0'
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

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--example-dir',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args()
    try:r=run(a.example_dir.resolve(),a.out_dir.resolve());print(json.dumps({'status':r['status'],'cases':len(r['cases'])}))
    except (ValueError,OSError,AssertionError,subprocess.TimeoutExpired) as e:p.exit(2,str(e)+'\n')
