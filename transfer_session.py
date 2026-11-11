"""Portable, credential-free checkpoints for emotional shape transfer."""
import copy
import json
import math
import os
import tempfile
from pathlib import Path
from analysis import AnalysisError, connection
from shape_transfer import prepare, target_layout
from session_identity import session_identity, timestamp

FORMAT='emotional-atlas-transfer-session-v1'


def checkpoint(source, signature, records, usage, complete=False, error=None, identity=None):
    return copy.deepcopy({'format':FORMAT, **session_identity('Transfer '+source['title'],identity),
        'saved_at':timestamp(), 'source':source, 'signature':list(signature),
        'records':{str(k):v for k,v in records.items()},'usage':usage,
        'complete':complete,'last_error':error})


def restore(data):
    def require(ok):
        if not ok:raise AnalysisError('Invalid or incompatible transfer checkpoint.')
    def number(value, low=-1, high=1, nullable=False):
        return (nullable and value is None) or (type(value) in (int,float) and math.isfinite(value) and low<=value<=high)
    def score(value,index):
        require(isinstance(value,dict) and value.get('id')==index)
        require(all(number(value.get(k),0 if k=='intensity' else -1,1,True) for k in ('valence','direction','intensity')))
    try:
        require(isinstance(data,dict) and data.get('format')==FORMAT)
        source=data['source'];require(isinstance(source,dict))
        require(isinstance(source['title'],str) and source['segmentation'] in ('blank','line','sentence'))
        connection(source['provider'],source['model'])
        require(type(source['total']) is int and source['total']>=2 and isinstance(source['rows'],list))
        ids=[]
        for row in source['rows']:
            index=row['id'];require(type(index) is int and 1<=index<=source['total']);score(row,index);ids.append(index)
        require(len(ids)==len(set(ids)))
        signature=data['signature'];require(isinstance(signature,list) and len(signature)==5)
        raw,mode,strength,attempts,policy=signature
        require(isinstance(raw,str) and mode in ('blank','sentence') and strength in ('25%','50%','75%','100%') and attempts in ('1','2') and policy in ('Flexible transformation','Preserve meaning'))
        units,_,desired=prepare(source['rows'],source['total'],raw,mode)
        require(isinstance(data['records'],dict));records={}
        for key,r in data['records'].items():
            require(isinstance(key,str) and key.isdigit());index=int(key)
            require(1<=index<=len(units) and index not in records and isinstance(r,dict) and r['id']==index)
            require(r['original']==units[index-1] and isinstance(r['text'],str) and bool(r['text'].strip()))
            require(type(r['accepted']) is bool and isinstance(r['fidelity'],str))
            for field in ('baseline','score'):score(r[field],index)
            for field in ('source_point','desired_point'):
                require(isinstance(r[field],list) and len(r[field])==3 and all(number(v) for v in r[field]))
            for field in ('before_error','after_error'):require(number(r[field],0,1,True))
            if 'final_score' in r:score(r['final_score'],index);require(number(r['final_error'],0,1,True))
            require(isinstance(r['attempts'],list))
            for trial in r['attempts']:
                require(isinstance(trial,dict) and isinstance(trial['text'],str) and isinstance(trial['changes'],str) and isinstance(trial['meaning_review'],dict))
                require(number(trial['error'],0,1,True))
            for error in r.get('processing_errors',[]):require(isinstance(error,dict) and isinstance(error['stage'],str) and isinstance(error['message'],str))
            records[index]=r
        require(type(data['complete']) is bool and (not data['complete'] or len(records)==len(units)))
        require(data.get('last_error') is None or isinstance(data['last_error'],str))
        require(isinstance(data['usage'],dict) and all(type(data['usage'].get(k)) is int and data['usage'][k]>=0 for k in ('input_tokens','output_tokens')))
        return {'source':copy.deepcopy(source),'signature':tuple(signature),'records':copy.deepcopy(records),
                'units':units,'desired':desired,'spans':target_layout(raw,mode),'usage':copy.deepcopy(data['usage']),
                'finished':data['complete'],'error':data.get('last_error'),'identity':session_identity('Transfer '+source['title'],data)}
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        raise AnalysisError('Invalid or incompatible transfer checkpoint.') from error


def write_checkpoint(path,data):
    # A failed/interrupted save never replaces the previous checkpoint.
    destination=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,prefix='.'+destination.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=stream.name
            json.dump(data,stream,ensure_ascii=False,indent=2,allow_nan=False)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,destination);temporary=None
    finally:
        if temporary is not None:Path(temporary).unlink(missing_ok=True)
