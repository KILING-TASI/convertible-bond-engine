// Original report interaction: select frozen core results; never reprice in-browser.
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('frozen-report').textContent);
  const d = data.result.diagnosis;
  const rows = [
    {group:'price', label:'输入全价', value:d.dirty_price, unit:'元 / 100 面值', status:'教学输入'},
    {group:'price', label:'纯债现值', value:d.bond_floor, unit:'元 / 100 面值', status:'假设曲线'},
    {group:'risk', label:'曲线平移修正久期', value:d.modified_duration_parallel, unit:'年', status:'固定现金流'},
    {group:'risk', label:'纯债 DV01', value:d.dv01, unit:'元 / 基点', status:'固定现金流'},
    ...Object.entries(d.yields).flatMap(([name, x]) => ['gross','net'].map(tax => ({group:'yield',label:`${name} · ${tax === 'gross' ? '税前' : '税后'}条件收益率`,value:x[tax] ?? null,unit:'年有效小数',status:'教学现金流'}))),
    ...Object.entries(data.result.event_chain.current_state).map(([name, state]) => ({group:'clause',label:`当前条款 · ${name}`,value:null,unit:'无数值',status:state}))
  ];
  const controls = ['category','search','sort'];
  const get = id => document.getElementById(id);
  function parameters() {
    return {category:get('category').value,search:get('search').value,sort:get('sort').value,
      scenarios:[...document.querySelectorAll('[name="scenario"]:checked')].map(x=>x.value)};
  }
  function selectedRows(p) {
    const filtered=rows.filter(r=>(p.category==='all'||r.group===p.category)&&r.label.toLowerCase().includes(p.search.toLowerCase()));
    filtered.sort((a,b)=>{
      if(p.sort==='name')return a.label.localeCompare(b.label,'zh-CN');
      if(a.value===null || b.value===null)return a.value===null ? (b.value===null?a.label.localeCompare(b.label):1):-1;
      // Different units are grouped, never ranked as comparable values.
      const unit=a.unit.localeCompare(b.unit,'zh-CN');
      return unit || (p.sort==='ascending'?a.value-b.value:b.value-a.value) || a.label.localeCompare(b.label);
    });
    return filtered;
  }
  function cells(tbody, values) {
    const tr=document.createElement('tr');
    for(const value of values){const td=document.createElement('td');td.textContent=String(value);tr.appendChild(td);}
    tbody.appendChild(tr);
  }
  function scenarios(p) {
    return p.scenarios.map(key=>key==='0'?{bps:0,price:d.bond_floor,approximation:d.bond_floor,approximation_error:0}: {bps:Number(key),...d.sensitivity_bps[key]});
  }
  function render() {
    const p=parameters(),visible=selectedRows(p);
    get('diagnostics').replaceChildren();
    for(const row of visible)cells(get('diagnostics'),[row.label,row.value===null?'未知 / 无数值':row.value.toFixed(8),row.unit,row.status]);
    get('row-count').textContent=`显示 ${visible.length} 项。未知没有变成 0；数值排序先按单位分组。`;
    get('scenario-results').replaceChildren();
    for(const row of scenarios(p))cells(get('scenario-results'),[`${row.bps>0?'+':''}${row.bps} bp`,row.price.toFixed(6),row.approximation.toFixed(6),row.approximation_error.toFixed(6)]);
    get('scenario-empty').textContent=p.scenarios.length?'':'尚未选择情景。';
  }
  controls.forEach(id=>get(id).addEventListener('input',render));
  document.querySelectorAll('[name="scenario"]').forEach(x=>x.addEventListener('change',render));
  get('save-view').addEventListener('click',()=>{
    const p=parameters();
    const output={type:'frozen-report-selection',schema_version:1,method_version:data.result.method_version,
      interaction_method_version:data.result.interaction_method_version,
      engine_version:data.result.engine_version,report_schema_version:data.result.report_schema_version,
      as_of:data.result.as_of,is_demo:true,input_sha256:data.result.input_sha256,result_sha256:data.result_sha256,
      parameters:p,inputs:data.inputs,source_result:data.result,
      visible_diagnostics:selectedRows(p),selected_scenarios:scenarios(p),
      calculation_mode:'select-precomputed-core-results; no browser repricing',
      limits:['教学全价；净价和实际应计息未提供','条件现金流收益率，不是预测','当前条款未知；无完整法律事件证据']};
    const blob=new Blob([JSON.stringify(output,null,2)+'\n'],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;
    link.download=`cb-selection-${data.result.as_of}-${Date.now()}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    get('saved-note').textContent='已请求另存新 JSON 文件；原输入与结果保持冻结。浏览器负责最终下载位置。';
  });
  render();
})();
