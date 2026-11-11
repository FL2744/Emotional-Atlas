"""Separate solid/evolving-object workspace. Main scatter plot remains untouched."""
import copy
from appearance import ui_color
import json
import math
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
import numpy as np
from geometry import METHODS, frame_mesh, description, obj_text, curved_surface, material_text
from pca import fit_pca
from evolution_export import write_evolution, ExportCancelled


def open_object_view(parent, plot_class):
    rows=copy.deepcopy(sorted(parent.results.values(),key=lambda r:r['id']))
    total=len(parent.paragraphs)
    snapshot_title=parent.title_text
    snapshot_unit='sentence' if parent.mode_used=='sentence' else 'paragraph'
    if not rows:
        messagebox.showinfo('Analyze text first','Object views need analyzed paragraph coordinates.',parent=parent);return
    win=tk.Toplevel(parent);win.title('Emotional Atlas · Solid & evolving object')
    win.geometry('1100x850');win.minsize(850,650);win.configure(background=ui_color('#111113'))
    state={'closed':False,'busy':False,'pending':False,'generation':0,'model':None,'meta':None,
           'playing':False,'timer':None,'exporting':False,'key':None,'samples':[]}
    events=queue.Queue();cache={};export_cancel=threading.Event()
    export_mode=tk.StringVar(value='Compact · all paragraphs')
    pca=fit_pca(rows)
    method=tk.StringVar(value=METHODS[0]);coordinates=tk.StringVar(value='Emotion axes')
    evolution=tk.StringVar(value='Whole text');size=tk.StringVar(value='1.0');window=tk.StringVar(value='20')
    frame=tk.DoubleVar(value=max(1,total));wire=tk.BooleanVar(value=False);points=tk.BooleanVar(value=False)
    axes=tk.BooleanVar(value=True)
    smoothing=tk.StringVar(value='Faceted');surface_color=tk.StringVar(value='#cccccc')
    status=tk.StringVar(value='Building geometry…');position=tk.StringVar()
    toolbar=ttk.Frame(win,padding=12);toolbar.pack(fill='x')
    def box(label,variable,values,width):
        group=ttk.Frame(toolbar);group.pack(side='left',padx=(0,10))
        ttk.Label(group,text=label,style='Muted.TLabel').pack(anchor='w')
        widget=ttk.Combobox(group,textvariable=variable,values=values,state='readonly',width=width)
        widget.pack();widget.bind('<<ComboboxSelected>>',lambda e:changed())
        return widget
    box('Surface',method,METHODS,22)
    box('Coordinates',coordinates,['Emotion axes','PCA 3D'],13)
    box('Evolution (fourth dimension)',evolution,['Whole text','Cumulative','Moving window'],17)
    params=ttk.Frame(win,padding=(12,0,12,6));params.pack(fill='x')
    group=ttk.Frame(params);group.pack(side='left',padx=(0,12))
    ttk.Label(group,text='Edge limit / tube radius',style='Muted.TLabel').pack()
    size_entry=ttk.Entry(group,textvariable=size,width=9);size_entry.pack()
    group=ttk.Frame(params);group.pack(side='left',padx=(0,12))
    ttk.Label(group,text='Window length (units)',style='Muted.TLabel').pack()
    window_entry=ttk.Entry(group,textvariable=window,width=7);window_entry.pack()
    smooth_group=ttk.Frame(params);smooth_group.pack(side='left',padx=8)
    ttk.Label(smooth_group,text='Surface finish',style='Muted.TLabel').pack()
    smooth_box=ttk.Combobox(smooth_group,textvariable=smoothing,values=['Faceted','Curved · 1','Curved · 2','Curved · 3'],state='readonly',width=13)
    smooth_box.pack();smooth_box.bind('<<ComboboxSelected>>',lambda e:changed())
    ttk.Button(params,text='Surface color…',command=lambda:choose_color()).pack(side='left',padx=5)
    ttk.Button(params,text='Apply',command=lambda:changed()).pack(side='left',padx=5)
    size_entry.bind('<Return>',lambda e:changed());window_entry.bind('<Return>',lambda e:changed())
    note=ttk.Label(win,text='Spatial neighbors use an edge-length limit; text-order tubes use a radius. All lengths use the chosen plot coordinates.',style='Muted.TLabel',wraplength=1000)
    note.pack(anchor='w',padx=12)

    class SolidPlot(plot_class):
        def __init__(self,master):
            self.solid=None;self.fit_scale=1.0;self.axis_mode='Emotion axes'
            super().__init__(master,lambda i:None)
        def project(self,p):return super().project([x/self.fit_scale for x in p])
        def draw_axes(self):
            if not axes.get():return
            bound=self.fit_scale
            origin=[-bound,-bound,-bound]
            labels=['X · Valence','Y · Direction','Z · 2 × Intensity − 1'] if self.axis_mode=='Emotion axes' else ['X · PC1 / scale','Y · PC2 / scale','Z · PC3 / scale']
            for axis,label in enumerate(labels):
                end=list(origin);end[axis]=bound
                x,y,_=self.project(origin);u,v,_=self.project(end)
                self.create_line(x,y,u,v,fill=ui_color('#aaaab0'),width=1.5,arrow='last',tags='object_axes')
                for value in (-bound,0,bound):
                    point=list(origin);point[axis]=value
                    tx,ty,_=self.project(point)
                    # Small screen-space ticks keep their size when the camera rotates.
                    self.create_line(tx-3,ty,tx+3,ty,fill=ui_color('#aaaab0'),tags='object_axes')
                    if value!=-bound or axis==0:
                        self.create_text(tx+5,ty+8,text=f'{value:.2g}',anchor='nw',fill=ui_color('#aaaab0'),font=('Helvetica Neue',9),tags='object_axes')
                label_point=list(end);label_point[axis]+=bound*.18
                lx,ly,_=self.project(label_point)
                lx=min(max(90,lx),max(90,self.winfo_width()-90));ly=min(max(25,ly),max(25,self.winfo_height()-45))
                self.create_text(lx,ly,text=label,fill=ui_color('#f2f2f3'),font=('Helvetica Neue',10),tags='object_axis_label')

        def draw(self):
            self.delete('all');self.points=[]
            if not self.solid:return
            model=self.solid;vertices=np.asarray(model['vertices'])
            projected=[self.project(p) for p in vertices]
            faces=sorted(model['faces'],key=lambda f:-sum(projected[i][2] for i in f)/3)
            if len(faces)>15000:
                self.draw_axes()
                self.create_text(self.winfo_width()/2,80,text='This surface exceeds the interactive limit of 15,000 triangles.\nUse a shorter moving window, or export the complete geometry.',fill=ui_color('#aaaab0'),width=700)
                return
            for face in faces:
                polygon=[value for i in face for value in projected[i][:2]]
                a,b,c=vertices[face];normal=np.cross(b-a,c-a);norm=np.linalg.norm(normal)
                shade=150 if norm==0 else int(100+105*abs(float(normal[2]/norm)))
                rgb=[int(surface_color.get()[i:i+2],16) for i in (1,3,5)]
                fill='#%02x%02x%02x'%tuple(round(c*shade/205) for c in rgb)
                self.create_polygon(*polygon,fill='' if wire.get() else fill,outline=surface_color.get() if wire.get() else fill,width=1)
            if points.get() or not faces:
                for p in model['input_points']:
                    x,y,_=self.project(p);self.create_oval(x-2,y-2,x+2,y+2,fill=ui_color('#f2f2f3'),outline='')
            self.draw_axes()
            if not faces:self.create_text(self.winfo_width()/2,40,text=model['message'],fill=ui_color('#aaaab0'),width=max(200,self.winfo_width()-60))
            self.create_text(14,self.winfo_height()-15,anchor='sw',fill=ui_color('#aaaab0'),text='Drag to rotate · Scroll to zoom · Fixed scale across frames')
    panes=tk.PanedWindow(win,orient='vertical',background=ui_color('#3d3d43'),borderwidth=0,sashwidth=9,showhandle=True,opaqueresize=True)
    panes.pack(fill='both',expand=True,padx=12,pady=6)
    plot_area=ttk.Frame(panes);details=ttk.Frame(panes)
    panes.add(plot_area,minsize=180,stretch='always');panes.add(details,minsize=180,stretch='never')
    plot=SolidPlot(plot_area);plot.pack(fill='both',expand=True,padx=12,pady=8)
    controls=ttk.Frame(plot_area,padding=(12,0));controls.pack(fill='x')
    ttk.Checkbutton(controls,text='Axes',variable=axes,command=plot.draw).pack(side='left',padx=(0,8))
    ttk.Checkbutton(controls,text='Wireframe',variable=wire,command=plot.draw).pack(side='left')
    ttk.Checkbutton(controls,text='Show source points',variable=points,command=plot.draw).pack(side='left',padx=10)
    ttk.Button(controls,text='Reset view',command=plot.reset).pack(side='left')
    play=ttk.Button(controls,text='Play evolution',command=lambda:toggle_play());play.pack(side='left',padx=10)
    ttk.Label(controls,textvariable=position,style='Muted.TLabel').pack(side='right')
    slider=ttk.Scale(plot_area,from_=1,to=max(1,total),variable=frame,command=lambda v:scrub())
    slider.pack(fill='x',padx=12,pady=6)
    details_header=ttk.Frame(details,padding=(12,4));details_header.pack(fill='x')
    ttk.Label(details_header,text='Object details · Drag the divider to resize',style='Muted.TLabel').pack(side='left')
    def expand_details():
        panes.update_idletasks()
        expanded=not state.get('details_expanded',False);state['details_expanded']=expanded
        panes.sash_place(0,0,max(180,round(panes.winfo_height()*(.35 if expanded else .6))))
        expand_button.configure(text='More plot space' if expanded else 'Expand details')
    expand_button=ttk.Button(details_header,text='Expand details',command=expand_details);expand_button.pack(side='right')
    info_card=ttk.Frame(details);info_card.pack(fill='both',expand=True,padx=12)
    info=tk.Text(info_card,height=6,wrap='word',background=ui_color('#19191c'),foreground=ui_color('#f2f2f3'),relief='flat',padx=10,pady=8)
    info_scroll=ttk.Scrollbar(info_card,orient='vertical',command=info.yview)
    info_scroll.pack(side='right',fill='y');info.configure(yscrollcommand=info_scroll.set)
    info.pack(fill='both',expand=True)
    export_options=ttk.Frame(details,padding=(12,2));export_options.pack(fill='x')
    ttk.Label(export_options,text='Evolution export',style='Muted.TLabel').pack(side='left',padx=(0,8))
    ttk.Combobox(export_options,textvariable=export_mode,values=['Compact · all paragraphs','Sampled meshes · up to 60'],state='readonly',width=28).pack(side='left')
    cancel_export=ttk.Button(export_options,text='Cancel export',state='disabled',command=lambda:export_cancel.set())
    cancel_export.pack(side='right')
    bar=ttk.Frame(details,padding=(12,6));bar.pack(fill='x')
    export_buttons=[]
    for index,(label,kind) in enumerate([('Export mesh (.obj)','obj'),('Export description (.txt)','txt'),('Export geometry (.json)','json'),('Export evolution (.json)','evolution')]):
        button=ttk.Button(bar,text=label,command=lambda k=kind:export(k));button.grid(row=index//2,column=index%2,sticky='ew',padx=(0,7),pady=2);export_buttons.append(button)
    status_card=ttk.Frame(details);status_card.pack(fill='x',padx=12,pady=(0,8))
    status_text=tk.Text(status_card,height=3,width=1,wrap='word',background=ui_color('#111113'),foreground=ui_color('#aaaab0'),
                        relief='flat',highlightthickness=0,state='disabled',font=('Helvetica Neue',11))
    status_scroll=ttk.Scrollbar(status_card,orient='vertical',command=status_text.yview)
    status_scroll.pack(side='right',fill='y');status_text.configure(yscrollcommand=status_scroll.set)
    status_text.pack(fill='x',expand=True)
    def update_status(*args):
        position=status_text.yview()[0]
        status_text.configure(state='normal');status_text.delete('1.0','end');status_text.insert('1.0',status.get())
        status_text.configure(state='disabled');status_text.yview_moveto(position)
    status.trace_add('write',update_status);update_status()

    def samples():
        if coordinates.get()=='PCA 3D':
            if pca['error']:raise ValueError(pca['error'])
            return [{'id':r['id'],'point':[x/pca['scale'] for x in pca['scores'][r['id']]]} for r in rows if r['id'] in pca['scores']]
        return [{'id':r['id'],'point':[r['valence'],r['direction'],2*r['intensity']-1]} for r in rows
                if all(type(r.get(k)) in (int,float) and math.isfinite(r[k]) for k in ('valence','direction','intensity'))]

    def settings():
        length=int(window.get());value=float(size.get())
        if length<1 or not math.isfinite(value) or not 0<value<=10:raise ValueError('Window must be a positive integer; size must be greater than 0 and at most 10.')
        i=max(1,min(max(1,total),round(frame.get())))
        meta={'coordinates':'x=valence, y=direction, z=2*intensity-1' if coordinates.get()=='Emotion axes' else 'p = PCA_score / global_PCA_scale; standardized PCA fitted once to the whole snapshot',
              'text_unit':snapshot_unit,'coordinate_mode':coordinates.get(),'evolution':evolution.get(),'frame':i,'total':total,'window':length,
              'subdivision_levels':0 if smoothing.get()=='Faceted' else int(smoothing.get()[-1]),'surface_color':surface_color.get(),'method':method.get(),'size':value,'title':snapshot_title,'snapshot_results':rows,
              'pca':pca if coordinates.get()=='PCA 3D' else None}
        return meta

    def choose_color():
        chosen=colorchooser.askcolor(color=surface_color.get(),parent=win,title='Object surface color')[1]
        if chosen:
            surface_color.set(chosen);changed()

    def changed():
        state['generation']+=1;state['pending']=True
        if not state['busy']:build()

    def build():
        if state['closed']:return
        state['pending']=False
        try:
            meta=settings();source=samples()
        except ValueError as e:
            state['model']=None;plot.solid=None;plot.draw();status.set(str(e));return
        key=(meta['coordinate_mode'],meta['method'],meta['evolution'],meta['frame'],meta['window'],meta['size'],meta['subdivision_levels'])
        position.set(f"¶ {meta['frame']} / {total} · Time τ={(meta['frame']-1)/max(1,total-1):.3f}")
        slider.configure(state='disabled' if evolution.get()=='Whole text' else 'normal')
        token=state['generation'];state['busy']=True
        if state['model'] is None:status.set('Building object from the analysis snapshot…')
        def worker():
            try:
                model=cache.get(key)
                if model is None:model=curved_surface(frame_mesh(source,meta['frame'],meta['evolution'],meta['window'],meta['method'],meta['size']),meta['subdivision_levels'])
                events.put(('mesh',(token,key,meta,source,model,None)))
            except Exception as e:events.put(('mesh',(token,key,meta,source,None,str(e))))
        threading.Thread(target=worker,daemon=True).start()

    def stop_play():
        state['playing']=False;play.configure(text='Play evolution')
        if state['timer'] is not None:win.after_cancel(state['timer']);state['timer']=None

    def tick():
        state['timer']=None
        if not state['playing'] or state['closed']:return
        if state['busy'] or state['pending']:state['timer']=win.after(80,tick);return
        if round(frame.get())>=total:stop_play();return
        frame.set(round(frame.get())+1);changed();state['timer']=win.after(350,tick)

    def toggle_play():
        if state['exporting']:
            status.set('Animation is paused during export. Cancel or wait for the export to finish.');return
        if state['playing']:stop_play();return
        if evolution.get()=='Whole text':evolution.set('Cumulative')
        if round(frame.get())>=total:frame.set(1)
        state['playing']=True;play.configure(text='Pause');changed();state['timer']=win.after(350,tick)

    def scrub():
        stop_play();changed()

    def export(kind):
        if state['busy'] or state['pending'] or state['model'] is None:
            messagebox.showinfo('Object not ready','Wait for a valid object calculation before exporting.',parent=win);return
        if state['exporting']:return
        if kind=='evolution' and state['meta']['evolution']=='Whole text':
            messagebox.showinfo('Select evolution','Choose Cumulative or Moving window first.',parent=win);return
        suffix='.'+('json' if kind=='evolution' else kind)
        path=filedialog.asksaveasfilename(parent=win,defaultextension=suffix,initialfile='emotional-atlas-'+kind+suffix)
        if not path:return
        stop_play()
        model=state['model'];meta=copy.deepcopy(state['meta']);source=list(state['samples']);mode=export_mode.get()
        export_cancel.clear();cancel_export.configure(state='normal')
        state['exporting']=True;status.set('Exporting…')
        def worker():
            try:
                if kind=='obj':
                    material=Path(path).with_suffix('.mtl')
                    payload='mtllib '+material.name+'\nusemtl atlas_surface\n'+obj_text(model)
                    material.write_text(material_text(meta['surface_color']),encoding='utf-8')
                elif kind=='txt':payload=description(model,meta)
                else:
                    data={'format':'emotional-atlas-object-v1','metadata':meta,'source_samples':source,'description':description(model,meta)}
                    if kind=='json':data['mesh']=model
                    else:
                        write_evolution(path,meta,source,description(model,meta),mode,export_cancel,
                                        lambda message:events.put(('export_progress',message)))
                        events.put(('export_done','Exported '+Path(path).name+' · '+mode));return
                    payload=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)
                # Prepare the entire export before replacing the requested destination.
                Path(path).write_text(payload,encoding='utf-8')
                events.put(('export_done','Exported '+Path(path).name))
            except ExportCancelled:events.put(('export_done','Export cancelled. Existing destination was left unchanged.'))
            except Exception as e:events.put(('export_done','Export failed: '+str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def poll():
        if state['closed']:return
        try:
            while True:
                kind,value=events.get_nowait()
                if kind=='mesh':
                    state['busy']=False;token,key,meta,source,model,error=value
                    if token==state['generation']:
                        if error:
                            state['model']=None;plot.solid=None;plot.draw();status.set('Could not build object: '+error)
                        else:
                            cache[key]=model
                            if len(cache)>24:cache.pop(next(iter(cache)))
                            state.update(model=model,meta=meta,samples=source,key=key)
                            plot.solid=model;plot.axis_mode=meta['coordinate_mode']
                            plot.fit_scale=max(1,max((abs(x) for r in source for x in r['point']),default=1)+(meta['size'] if meta['method']==METHODS[2] else 0))
                            plot.draw();reading_position=info.yview()[0]
                            info.configure(state='normal');info.delete('1.0','end');info.insert('end',description(model,meta));info.configure(state='disabled');info.yview_moveto(reading_position)
                            status.set(f"Snapshot: {len(source)}/{total} text units with coordinates · {len(model['faces'])} triangles · {model['message']} Reopen this view to use newer analysis results.")
                    if state['pending']:build()
                elif kind=='export_progress':status.set(value)
                elif kind=='export_done':
                    state['exporting']=False;cancel_export.configure(state='disabled');status.set(value)
        except queue.Empty:pass
        win.after(50,poll)

    def close():
        stop_play();export_cancel.set();state['closed']=True;win.destroy()
    win.protocol('WM_DELETE_WINDOW',close)
    win.bind('<Escape>',lambda e:close())
    # Expose a small test/automation interface without coupling the main plot state.
    win.object_controls={'method':method,'evolution':evolution,'frame':frame,'size':size,'window':window,'coordinates':coordinates,
                         'export_mode':export_mode,'export_cancel':export_cancel,'panes':panes,'status':status,'status_text':status_text,'expand_details':expand_details,'axes':axes,'smoothing':smoothing,'surface_color':surface_color,'choose_color':choose_color,'state':state,'plot':plot,'changed':changed,'close':close,'export':export,'play':toggle_play}
    changed();poll()
    return win
