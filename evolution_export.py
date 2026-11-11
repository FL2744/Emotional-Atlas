"""Bounded, cancellable evolution exports; compact exports never rebuild geometry."""
import json
import os
import tempfile
from pathlib import Path
from geometry import frame_mesh, curved_surface

class ExportCancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel.is_set():raise ExportCancelled()


def write_evolution(path,meta,source,description,mode,cancel,progress=lambda s:None):
    if mode not in ('Compact · all paragraphs','Sampled meshes · up to 60'):raise ValueError('Unknown export mode.')
    total=meta['total'];sampled=mode.startswith('Sampled')
    indices=sorted({1+round(i*(total-1)/59) for i in range(60)}) if total>1 else [1]
    selected=set(indices) if sampled else set()
    header={'format':'emotional-atlas-evolution-v2','metadata':meta,'source_samples':source,'description':description,
            'representation':'sampled meshes plus complete reconstruction data' if sampled else 'complete reconstruction data; meshes not precomputed',
            'mesh_paragraphs':indices if sampled else [],'frame_count':total,
            'reconstruction':'For each paragraph i use source IDs <= i (Cumulative), or max(1,i-window+1) <= ID <= i (Moving window); apply method, size and Loop subdivision_levels from metadata. Coordinates and PCA transform are fixed across frames.',
            'hypervolume':None,'hypervolume_note':'Not computed. Requires evaluating every 3D time slice.'}
    destination=Path(path);temporary=None;triangles=0
    try:
        check_cancel(cancel)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,prefix='.'+destination.name+'.',suffix='.tmp',delete=False) as out:
            temporary=out.name
            # Stream large metadata and frame records; retain only one computed mesh.
            encoder=json.JSONEncoder(ensure_ascii=False,allow_nan=False,separators=(',',':'))
            def emit(value):
                for n,chunk in enumerate(encoder.iterencode(value)):
                    if n%256==0:check_cancel(cancel)
                    out.write(chunk)
            out.write('{')
            for key,value in header.items():
                out.write(json.dumps(key)+':');emit(value);out.write(',')
            out.write('"frames":[')
            for i in range(1,total+1):
                check_cancel(cancel)
                record={'paragraph':i,'tau':(i-1)/max(1,total-1)}
                if i in selected:
                    first=max(1,i-meta['window']+1) if meta['evolution']=='Moving window' else 1
                    count=sum(first<=r['id']<=i for r in source)
                    if count>1500:raise ValueError('A sampled frame exceeds 1,500 points. Use Compact export or a smaller moving window.')
                    base=frame_mesh(source,i,meta['evolution'],meta['window'],meta['method'],meta['size'])
                    expected=len(base['faces'])*4**meta['subdivision_levels']
                    if expected>20000 or triangles+expected>250000:raise ValueError('Mesh export exceeds its geometry budget. Use Compact export or lower curvature/window size.')
                    record['mesh']=curved_surface(base,meta['subdivision_levels'],cancel=cancel)
                    triangles+=len(record['mesh']['faces'])
                    # Yield between expensive frames, and make cancellation responsive.
                    if cancel.wait(.03):raise ExportCancelled()
                if i>1:out.write(',')
                emit(record)
                if i%10==0 or i==total:progress(f'Exporting evolution: {i}/{total} paragraph records…')
            out.write(']}')
        check_cancel(cancel)
        os.replace(temporary,destination);temporary=None
    finally:
        if temporary is not None:
            try:os.unlink(temporary)
            except FileNotFoundError:pass
