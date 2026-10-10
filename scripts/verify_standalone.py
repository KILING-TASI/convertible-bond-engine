"""Real non-editable wheel acceptance in a fresh directory/process/venv."""
import argparse,hashlib,json,os,subprocess,sys,venv
from pathlib import Path


def verify(wheel,destination):
    wheel=wheel.resolve();root=destination.resolve();root.mkdir(parents=True,exist_ok=False)
    home=root/'empty-home';home.mkdir();cwd=root/'run';cwd.mkdir()
    env=dict(os.environ)
    removed=[]
    for key in list(env):
        if key in ('PYTHONPATH','PYTHONHOME') or any(marker in key for marker in ('RESEARCH_WORKBENCH','COMPONENT_PATH','ENGINE_ROOT','SKILL_PATH')) or key.endswith(('_PROJECT_DIR','_COMPONENT_PATH','_DATA_DIR','_SKILL_PATH')):
            removed.append(key);env.pop(key)
    # Child environment only; no mutation of system HOME, user caches, or CODEX_HOME.
    for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA','XDG_CACHE_HOME','PIP_CACHE_DIR'):
        env[key]=str(home/key.lower())
        Path(env[key]).mkdir(parents=True)
    env['PYTHONIOENCODING']='utf-8';env['PYTHONNOUSERSITE']='1'
    virtual=root/'venv';venv.EnvBuilder(with_pip=True,system_site_packages=False).create(virtual)
    python=virtual/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    commands=[]
    def run(args,expected=0):
        r=subprocess.run([str(python),*map(str,args)],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=90)
        commands.append({'args':list(map(str,args)),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode!=expected:raise RuntimeError('unexpected command result: '+str(commands[-1]))
        return r
    run(['-m','pip','install','--no-deps','--no-cache-dir',wheel])
    probe=run(['-c',"import json,sys,sysconfig,importlib.util,importlib.metadata as m,cbengine,cbengine.preview,cbengine.crosscheck,cbengine.bridge,cbengine.scenarios; print(json.dumps({'python':sys.version,'prefix':sys.prefix,'path':sys.path,'module_origin':cbengine.__file__,'module_origins':{x:sys.modules[x].__file__ for x in ['cbengine','cbengine.engine','cbengine.preview','cbengine.crosscheck','cbengine.bridge','cbengine.scenarios']},'data':sysconfig.get_path('data'),'version':m.version('convertible-bond-engine'),'dependencies':{x:importlib.util.find_spec(x) is not None for x in ['akshare','pypdf','QuantLib']},'installed':{d.metadata['Name']:d.version for d in m.distributions()}}))"])
    origins=json.loads(probe.stdout)
    assert all(Path(origin).resolve().is_relative_to(virtual) for origin in origins['module_origins'].values())
    assert not any('research-workbench' in p.lower() for p in origins['path'])
    assert all(not found for found in origins['dependencies'].values())
    packaged=Path(origins['data'])/'share/convertible-bond-engine';examples=packaged/'examples'
    for file in ('LICENSE','README.md','DISCLAIMER.md','THIRD_PARTY_NOTICES.md'):
        assert (packaged/file).is_file(),file
    run(['-m','cbengine.preview',examples/'demo.json','--out-dir',cwd/'preview'])
    result=json.loads((cwd/'preview/result.json').read_text(encoding='utf-8'))
    assert result['is_demo'] and result['engine_version']==origins['version']
    d=result['diagnosis'];assert d['dirty_price']==118.5 and abs(d['bond_floor']-95.10939701857427)<1e-10
    assert abs(d['yields']['maturity']['gross']-(-.011218746052657966))<1e-12
    assert all(v=='unknown' for v in result['event_chain']['current_state'].values())
    before=hashlib.sha256((cwd/'preview/result.json').read_bytes()).hexdigest()
    run(['-m','cbengine.preview',examples/'demo.json','--out-dir',cwd/'preview'],2)
    assert before==hashlib.sha256((cwd/'preview/result.json').read_bytes()).hexdigest()
    run(['-m','cbengine.crosscheck',examples/'crosscheck-flat.json','--quantlib'],2)
    run(['-m','cbengine.crosscheck',examples/'crosscheck-flat.json','--out',cwd/'core-check.json'])
    assert json.loads((cwd/'core-check.json').read_text(encoding='utf-8'))['external']['status']=='not-run'
    run(['-m','cbengine.bridge',examples/'bridge-fixed-demo.json','--out-dir',cwd/'bridge'])
    run(['-m','cbengine.scenarios','--example-dir',examples,'--out-dir',cwd/'scenarios'])
    scenario_summary=json.loads((cwd/'scenarios/summary.json').read_text(encoding='utf-8'))
    assert scenario_summary['status']=='passed' and len(scenario_summary['cases'])==12
    run(['-m','cbengine.scenarios','--cn-only','--example-dir',examples,'--out-dir',cwd/'cn-scenarios'])
    cn_summary=json.loads((cwd/'cn-scenarios/summary.json').read_text(encoding='utf-8'))
    assert cn_summary['status']=='passed' and cn_summary['groups']==4 and cn_summary['cli_cases']==5
    import re
    for name in ('input.json','result.json'):
        assert (cwd/'preview'/name).is_file()
    for link in re.findall(r'href="([^"]+)"',(cwd/'preview/report.html').read_text(encoding='utf-8')):
        if not link.startswith(('https:','http:','#')):assert (cwd/'preview'/link).is_file(),link
    record={'scope':'isolated directory/process/venv on existing host; not fresh OS','status':'passed',
      'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'origins':origins,'removed_variable_names':removed,
      'commands':commands,'report_checks':{'teaching':True,'dirty_price':d['dirty_price'],'bond_floor':d['bond_floor'],'gross_yield':d['yields']['maturity']['gross'],'rights':'unknown','file_links':'passed'},
      'visual':'not inspected in this batch','real_network_data':'not requested','old_release':'not tested in this batch'}
    (root/'acceptance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wheel',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);a=p.parse_args()
    result=verify(a.wheel,a.work_dir);print(json.dumps({'status':result['status'],'module_origin':result['origins']['module_origin']},ensure_ascii=False))
