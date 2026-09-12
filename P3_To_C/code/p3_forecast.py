"""按发行时可见历史建立不可变预测和成熟配对残差。"""
import io
from pathlib import Path
import numpy as np
import pandas as pd
from p3_io import digest,write_csv,save_json,read_json,atomic_write_bytes,append_json
from p3_data import stamp

def forecast_asof(history,day,hour,hourly,branch):
    cutoff=day*144+hour*6
    if history.shape!=(cutoff,2): raise ValueError('history必须恰好截断至发行边界')
    if hourly.shape!=(24,) or not np.isfinite(hourly).all() or np.any(hourly<0): raise ValueError('发行预报非法')
    if not np.isfinite(history).all() or np.any(history<0): raise ValueError('可见历史非法')
    if day<7 or branch not in ('PREFIX','NO_PREFIX'): raise ValueError('发行范围或分支错误')
    target=np.arange(cutoff,cutoff+144);source=target-1008
    if source.max()>=cutoff or source.min()<0: raise ValueError('W1不是过去数据')
    baseline=history[source,0].copy();m=144-hour*6
    fit={'fit_id':f'PREFIX/{stamp(cutoff)}','issue_datetime':stamp(cutoff),'issue_hour':hour,
         'train_dates':[],'sample_count':0,'alpha':0.,'beta':0.,'delta_kw':0.,'current_x_kw':None,
         'x_q05':None,'x_q95':None,'y_q05':None,'y_q95':None,'max_label_end':None,'fallback':'无前缀修正'}
    if branch=='PREFIX' and hour:
        train=np.arange(max(7,day-56),day);count=len(train);past=history[:,0]
        xnow=float(np.mean(past[day*144:cutoff]-past[(day-7)*144:cutoff-1008]))
        fit.update(train_dates=[stamp(s*144)[:10] for s in train],sample_count=count,current_x_kw=xnow,
                   max_label_end=stamp(day*144) if count else None,fallback='样本不足14日')
        if count>=14:
            errors=np.array([past[s*144:(s+1)*144]-past[(s-7)*144:(s-6)*144] for s in train])
            x=errors[:,:hour*6].mean(1);y=errors[:,hour*6:].mean(1)
            xq=np.quantile(x,[.05,.95],method='linear');yq=np.quantile(y,[.05,.95],method='linear')
            xx=np.clip(x,*xq);yy=np.clip(y,*yq);xc=xx-xx.mean();yc=yy-yy.mean()
            fit.update(x_q05=float(xq[0]),x_q95=float(xq[1]),y_q05=float(yq[0]),y_q95=float(yq[1]))
            if np.mean(xc**2)<=1e-12: fit['fallback']='中心化方差退化'
            else:
                beta=float(np.clip(np.dot(xc,yc)/(1.1*np.dot(xc,xc)),0,1));alpha=float(yy.mean()-beta*xx.mean())
                delta=float(np.clip(alpha+beta*np.clip(xnow,*xq),*yq))
                fit.update(alpha=alpha,beta=beta,delta_kw=delta,fallback='无')
    load=baseline.copy();load[:m]=np.maximum(0,load[:m]+fit['delta_kw'])
    nodes=np.r_[history[-1,1],hourly]
    j=np.arange(144);left=j//6;w=(j%6+.5)/6
    pv=(1-w)*nodes[left]+w*nodes[left+1]
    provenance={'cutoff':cutoff,'branch':branch,'source_slots':source.tolist(),'anchor_slot_end':cutoff,
                'hourly':hourly.tolist(),'fit':fit,'load_kw':load.tolist(),'pv_kw':pv.tolist()}
    return {'load_kw':load,'pv_kw':pv,'w1_kw':baseline,'fit':fit,'source_slots':source,
            'anchor_kw':float(nodes[0]),'version':digest(provenance),'information_signature':digest(provenance)}

class Forecasts:
    def __init__(self,arrays,metadata):
        self.arrays=arrays;self.metadata=metadata
    def context(self,day,hour,branch):
        idx=(day-7)*4+hour//6;b=0 if branch=='PREFIX' else 1
        eligible=[s for s in range(hour//6,idx,4) if self.arrays['cutoff'][s]+144<=self.arrays['cutoff'][idx] and self.arrays['complete'][s]]
        members=eligible[-28:]
        if len(members)<14: raise RuntimeError('正式发行成熟情景不足14条')
        rawl=self.arrays['load'][b,idx]+self.arrays['eload'][b,members]
        rawpv=self.arrays['pv'][idx]+self.arrays['epv'][members]
        return {'load_kwh':np.maximum(rawl,0)/6,'pv_kwh':np.maximum(rawpv,0)/6,
                'source_issues':[stamp(self.arrays['cutoff'][s]) for s in members],
                'source_versions':[self.metadata['versions'][b][s] for s in members],
                'forecast_version':self.metadata['versions'][b][idx],
                'projection_load':np.sum(rawl<0,axis=1),'projection_pv':np.sum(rawpv<0,axis=1),
                'idx':idx,'member_idx':members,'branch':branch,
                'information_signature':digest({'forecast_version':self.metadata['versions'][b][idx],
                  'sources':[self.metadata['versions'][b][s] for s in members],
                  'l':np.maximum(rawl,0),'pv':np.maximum(rawpv,0)})}

def build_forecasts(data,signature,journal):
    base=data.base;cache=base/'logs/forecast_cache.npz';meta_path=base/'logs/forecast_metadata.json'
    if cache.exists() or meta_path.exists():
        if not(cache.exists() and meta_path.exists()): raise RuntimeError('预测缓存事务不完整；保留证据，停止')
        meta=read_json(meta_path)
        from p3_io import file_hash
        if meta['signature']!=signature or file_hash(cache)!=meta['cache_sha256']: raise RuntimeError('预测缓存签名冲突')
        journal.info.update(prefix_estimation_calls=meta['fit_calls'],prefix_successful_fits=meta['successful_fits']);journal.sync()
        with np.load(cache,allow_pickle=False) as z: arrays={k:z[k] for k in z.files}
        return Forecasts(arrays,meta)
    fit_journal=base/'logs/prefix_estimation_calls.jsonl'
    if fit_journal.exists():
        raise RuntimeError('已有前缀估计调用但完整预测缓存缺失；保留证据，不重复拟合')
    n=1432
    arrays={'load':np.empty((2,n,144)), 'w1':np.empty((n,144)), 'pv':np.empty((n,144)),
            'eload':np.zeros((2,n,144)), 'epv':np.zeros((n,144)),
            'cutoff':np.array([(d*144+h*6) for d in range(7,365) for h in (0,6,12,18)]),
            'complete':np.zeros(n,dtype=bool)}
    meta={'signature':signature,'versions':[[],[]],'fits':[],'fit_calls':0,'successful_fits':0}
    ledger=[];membership=[];quantiles=[];registry=[]
    for i,cutoff in enumerate(arrays['cutoff']):
        cutoff=int(cutoff);d=cutoff//144;h=(cutoff%144)//6
        hist=data.history(cutoff);hourly=data.issue(d,h)
        # 只在新的发行边界注册已完成的历史路径；从不将未来标签带入预测函数。
        for source in range(max(0,i-4),i):
            if not arrays['complete'][source] and arrays['cutoff'][source]+144<=cutoff:
                sc=int(arrays['cutoff'][source]);truth=hist[sc:sc+144]
                if len(truth)!=144: raise RuntimeError('残差标签未完整')
                arrays['eload'][:,source]=truth[:,0]-arrays['load'][:,source]
                arrays['epv'][source]=truth[:,1]-arrays['pv'][source];arrays['complete'][source]=True
        for b,branch in enumerate(('PREFIX','NO_PREFIX')):
            if b==0 and h:
                append_json(fit_journal,{'event':'START','fit_id':f'PREFIX/{stamp(cutoff)}','production_estimation':True})
                journal.info['prefix_estimation_calls']=meta['fit_calls']+1
            f=forecast_asof(hist,d,h,hourly,branch)
            if b==0 and h:
                append_json(fit_journal,{'event':'END','fit_id':f['fit']['fit_id'],'fit':f['fit']})
            arrays['load'][b,i]=f['load_kw'];arrays['w1'][i]=f['w1_kw'];arrays['pv'][i]=f['pv_kw']
            meta['versions'][b].append(f['version'])
            if b==0 and h:
                meta['fits'].append(f['fit']);meta['fit_calls']+=1;meta['successful_fits']+=f['fit']['fallback']=='无'
            for j in range(144):
                target=cutoff+j
                ledger.append({'forecast_branch':branch,'issue_datetime':stamp(cutoff),'issue_hour':h,
                    'forecast_version':f['version'],'target_interval_start':stamp(target),'target_interval_end':stamp(target+1),
                    'lead_slot':j+1,'horizon_class':'当日剩余' if target//144==d else '次日延续',
                    'load_forecast_kw':f['load_kw'][j],'pv_forecast_kw':f['pv_kw'][j],
                    'load_forecast_kwh':f['load_kw'][j]/6,'pv_forecast_kwh':f['pv_kw'][j]/6,
                    'w1_kw':f['w1_kw'][j],'w1_source_end':stamp(f['source_slots'][j]+1),
                    'anchor_end':stamp(cutoff),'anchor_kw':f['anchor_kw'],
                    'fit_id':f['fit']['fit_id'] if b==0 and h else '无'})
            if d>=31:
                context=Forecasts(arrays,meta).context(d,h,branch)
                for k,source in enumerate(context['member_idx']):
                    membership.append({'forecast_branch':branch,'issue_datetime':stamp(cutoff),
                        'scenario_id':k,'source_issue':stamp(arrays['cutoff'][source]),
                        'source_version':meta['versions'][b][source], 'mature_end':stamp(arrays['cutoff'][source]+144),
                        'weight':1/len(context['member_idx']),'projection_load':context['projection_load'][k],
                        'projection_pv':context['projection_pv'][k]})
                net=context['load_kwh']-context['pv_kwh'];q=np.quantile(net,[.05,.5,.95],axis=0)
                for j in range(144): quantiles.append({'forecast_branch':branch,'issue_datetime':stamp(cutoff),'lead_slot':j+1,
                    'sample_count':len(context['member_idx']),'net_q05_kwh':q[0,j],'net_q50_kwh':q[1,j],'net_q95_kwh':q[2,j],
                    'usage':'条件情景诊断，非真实标签'})
        if i%100==0: journal.check_budget()
    # 最后一个可见边界为2026-01-01 00:00，只注册完整标签；其余不造actual。
    hist=data.history(52560)
    for i,cutoff in enumerate(arrays['cutoff']):
        if cutoff+144<=52560 and not arrays['complete'][i]:
            truth=hist[cutoff:cutoff+144];arrays['eload'][:,i]=truth[:,0]-arrays['load'][:,i]
            arrays['epv'][i]=truth[:,1]-arrays['pv'][i];arrays['complete'][i]=True
        for b,branch in enumerate(('PREFIX','NO_PREFIX')):
            registry.append({'forecast_branch':branch,'source_issue':stamp(cutoff),'source_version':meta['versions'][b][i],
                'target_end':stamp(cutoff+144),'maturity_time':stamp(cutoff+144) if arrays['complete'][i] else '',
                'complete':bool(arrays['complete'][i]),'status':'完整成熟' if arrays['complete'][i] else '跨年标签不可用'})
    if meta['fit_calls']>1074 or meta['successful_fits']>1032: raise RuntimeError('回归调用预算超限')
    write_csv(base/'results/p3_forecast_ledger.csv',ledger)
    fits=[{**r,'train_dates':'|'.join(r['train_dates'])} for r in meta['fits']]
    write_csv(base/'results/p3_load_fit_log.csv',fits)
    write_csv(base/'results/p3_residual_path_registry.csv',registry)
    write_csv(base/'results/p3_scenario_membership.csv',membership)
    write_csv(base/'results/p3_scenario_quantile_diagnostics.csv',quantiles)
    buf=io.BytesIO();np.savez_compressed(buf,**arrays);atomic_write_bytes(cache,buf.getvalue())
    from p3_io import file_hash
    meta['cache_sha256']=file_hash(cache);save_json(meta_path,meta)
    journal.info.update(prefix_estimation_calls=meta['fit_calls'],prefix_successful_fits=meta['successful_fits']);journal.sync()
    return Forecasts(arrays,meta)
