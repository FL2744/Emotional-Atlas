"""Separate target rewriting workspace, preserving the source Atlas session."""
import copy
from appearance import ui_color
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime,timezone
from analysis import AnalysisError, Cancelled
from transfer_session import checkpoint, restore, write_checkpoint
from session_identity import session_identity, session_filename, timestamp
from shape_transfer import prepare, trajectory, run_transfer, target_layout, assemble_target


def open_saved_transfer(parent,plot_class):
    path=filedialog.askopenfilename(parent=parent,filetypes=[('Transfer checkpoint','*.json')])
    if not path:return
    try:saved=restore(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError,ValueError,AnalysisError) as error:
        messagebox.showerror('Cannot open transfer',str(error),parent=parent);return
    return open_transfer(parent,plot_class,saved=saved)


def open_transfer(parent,plot_class,saved=None):
    source_rows=copy.deepcopy(saved['source']['rows'] if saved else list(parent.results.values()))
    source_total=saved['source']['total'] if saved else len(parent.paragraphs)
    try:knots=trajectory(source_rows,source_total)
    except AnalysisError as e:messagebox.showinfo('Source analysis needed',str(e),parent=parent);return
    provider=parent.session_provider;model=parent.session_model
    source_title=parent.title_text;source_mode=parent.mode_used
    if saved:
        provider=saved['source']['provider'];model=saved['source']['model']
        source_title=saved['source']['title'];source_mode=saved['source']['segmentation']
    source_snapshot={'rows':source_rows,'total':source_total,'title':source_title,'segmentation':source_mode,'provider':provider,'model':model}
    win=tk.Toplevel(parent);win.title('Emotional Atlas · Emotional shape transfer')
    win.geometry('1180x850');win.minsize(860,650);win.configure(background=ui_color('#111113'))
    state={'running':False,'closed':False,'records':{},'signature':None,'units':[], 'desired':[], 'spans':[],
           'usage':{'input_tokens':0,'output_tokens':0},'dirty':False,'finished':False,'error':None,'identity':session_identity('Transfer '+source_title)}
    cancel=threading.Event();events=queue.Queue()
    unit_mode=tk.StringVar(value='Sentences' if source_mode=='sentence' else 'Paragraphs')
    preservation=tk.StringVar(value='Flexible transformation')
    strength=tk.StringVar(value='100%');attempts=tk.StringVar(value='1');status=tk.StringVar(value='Add target text, then transfer the source emotional trajectory.')
    top=ttk.Frame(win,padding=12);top.pack(fill='x')
    heading=ttk.Frame(top);heading.pack(fill='x')
    ttk.Label(heading,text='Emotional shape transfer',style='Heading.TLabel').pack(side='left',anchor='n',padx=(0,16))
    status_label=tk.Text(heading,width=48,height=3,wrap='word',background=ui_color('#111113'),foreground=ui_color('#f2f2f3'),relief='flat',borderwidth=0,highlightthickness=0,state='disabled',padx=0,font=('Helvetica Neue',11),cursor='arrow')
    status_label.tag_configure('status',justify='right')
    status_label.pack(side='right',fill='x',expand=True,anchor='n')
    ttk.Label(top,text=f'Source: {source_title} · {len(knots)}/{source_total} units with coordinates · {provider} / {model}',style='Muted.TLabel',wraplength=1050).pack(anchor='w',pady=5)
    ttk.Label(top,text='Uses the source analysis provider/model for comparable scores. Source gaps are interpolated. Flexible mode prioritizes emotional shape and permits meaning changes.',style='Muted.TLabel',wraplength=1050).pack(anchor='w')
    files=ttk.Frame(win,padding=(12,0));files.pack(fill='x')
    ttk.Button(files,text='Open transfer',command=lambda:open_saved_transfer(parent,plot_class)).pack(side='left')
    ttk.Button(files,text='Save transfer',command=lambda:save_transfer()).pack(side='left',padx=8)
    actions=ttk.Frame(win,padding=(12,0));actions.pack(fill='x')
    open_btn=ttk.Button(actions,text='Open target .txt',command=lambda:open_target());open_btn.pack(side='left')
    ttk.Label(actions,text='Target units').pack(side='left',padx=(12,4))
    mode_box=ttk.Combobox(actions,textvariable=unit_mode,values=['Paragraphs','Sentences'],state='readonly',width=11);mode_box.pack(side='left')
    ttk.Label(actions,text='Transfer strength').pack(side='left',padx=(12,4))
    strength_box=ttk.Combobox(actions,textvariable=strength,values=['25%','50%','75%','100%'],state='readonly',width=6);strength_box.pack(side='left')
    ttk.Label(actions,text='Attempts').pack(side='left',padx=(12,4))
    attempt_box=ttk.Combobox(actions,textvariable=attempts,values=['1','2'],state='readonly',width=3);attempt_box.pack(side='left')
    policy_row=ttk.Frame(win,padding=(12,6));policy_row.pack(fill='x')
    ttk.Label(policy_row,text='Editing policy').pack(side='left',padx=(0,8))
    policy_box=ttk.Combobox(policy_row,textvariable=preservation,values=['Flexible transformation','Preserve meaning'],state='readonly',width=24);policy_box.pack(side='left')
    ttk.Label(policy_row,text='Flexible: closest reasonable revision; meaning changes are reported.',style='Muted.TLabel').pack(side='left',padx=12)
    run_actions=ttk.Frame(win,padding=(12,6));run_actions.pack(fill='x')
    ttk.Label(run_actions,text='Whole documents supported. Long paragraphs are processed as passages automatically; up to 5 model calls per batch, plus retries.',style='Muted.TLabel',wraplength=450).pack(side='left')
    run_btn=ttk.Button(run_actions,text='Transfer / Resume',command=lambda:start());run_btn.pack(side='left',padx=8)
    stop_btn=ttk.Button(run_actions,text='Stop',command=lambda:stop(),state='disabled');stop_btn.pack(side='left')
    notebook=ttk.Notebook(win);notebook.pack(fill='both',expand=True,padx=12,pady=10)
    texts=ttk.Frame(notebook);notebook.add(texts,text='Target & revision')
    comparison=ttk.Frame(notebook);notebook.add(comparison,text='Geometry & meaning review')
    text_panes=ttk.Panedwindow(texts,orient='horizontal');text_panes.pack(fill='both',expand=True)
    def editor(title,readonly=False):
        card=ttk.Frame(text_panes,padding=6);text_panes.add(card,weight=1)
        ttk.Label(card,text=title,style='Heading.TLabel').pack(anchor='w',pady=(0,5))
        inner=ttk.Frame(card);inner.pack(fill='both',expand=True)
        text=tk.Text(inner,wrap='word',width=40,height=12,background=ui_color('#19191c'),foreground=ui_color('#f2f2f3'),insertbackground=ui_color('#f2f2f3'),relief='flat',padx=10,pady=10,undo=not readonly)
        scroll=ttk.Scrollbar(inner,orient='vertical',command=text.yview);scroll.pack(side='right',fill='y');text.configure(yscrollcommand=scroll.set);text.pack(fill='both',expand=True)
        if readonly:text.configure(state='disabled')
        return text
    target=editor('Original target');revised=editor('Revised target',True)
    charts=ttk.Frame(comparison);charts.pack(fill='both',expand=True)
    plots=[]
    for label in ('Requested trajectory','Original target','Revised target'):
        card=ttk.Frame(charts);card.pack(side='left',fill='both',expand=True)
        ttk.Label(card,text=label,style='Heading.TLabel').pack()
        plot=plot_class(card,lambda i:inspect(i));plot.configure(width=300,height=260);plot.show_trail=True;plot.pack(fill='both',expand=True);plots.append(plot)
    summary=tk.StringVar(value='Run a transfer to compare geometry and semantic review.')
    ttk.Label(comparison,textvariable=summary,style='Muted.TLabel',wraplength=1050).pack(anchor='w',pady=5)
    log_card=ttk.Frame(comparison);log_card.pack(fill='x')
    log=tk.Text(log_card,height=9,wrap='word',background=ui_color('#19191c'),foreground=ui_color('#f2f2f3'),relief='flat',padx=10,pady=8,state='disabled')
    log_scroll=ttk.Scrollbar(log_card,orient='vertical',command=log.yview);log_scroll.pack(side='right',fill='y')
    log.configure(yscrollcommand=log_scroll.set);log.pack(fill='x',expand=True)
    bottom=ttk.Frame(win,padding=12);bottom.pack(fill='x')
    ttk.Button(bottom,text='Export revised .txt',command=lambda:save('txt')).pack(side='left')
    ttk.Button(bottom,text='Export transfer report .json',command=lambda:save('json')).pack(side='left',padx=8)
    ttk.Label(bottom,text='LLM meaning checks and geometry scores require human review.',style='Muted.TLabel').pack(side='left',padx=8)
    def status_changed(*args):
        status_label.configure(state='normal');status_label.delete('1.0','end');status_label.insert('1.0',status.get(),'status');status_label.configure(state='disabled');status_label.yview_moveto(0)
    status.trace_add('write',status_changed);status_changed()

    def mode():return 'sentence' if unit_mode.get()=='Sentences' else 'blank'
    def output():
        return assemble_target(state['signature'][0],state['spans'],state['records']) if state['signature'] else ''
    def busy(value):
        state['running']=value
        for button in (open_btn,run_btn):button.configure(state='disabled' if value else 'normal')
        for widget in (mode_box,strength_box,attempt_box,policy_box):widget.configure(state='disabled' if value else 'readonly')
        target.configure(state='disabled' if value else 'normal');stop_btn.configure(state='normal' if value else 'disabled')
    def start():
        if state['running']:return
        key=parent.api_keys[provider].get().strip()
        if not key:messagebox.showinfo('API key needed',f'Enter the {provider} key in the main window. This transfer uses the source model {model}.',parent=win);return
        raw=target.get('1.0','end-1c')
        try:units,_,desired=prepare(source_rows,source_total,raw,mode())
        except AnalysisError as e:messagebox.showerror('Cannot transfer',str(e),parent=win);return
        signature=(raw,mode(),strength.get(),attempts.get(),preservation.get())
        if signature!=state['signature']:
            if state['dirty'] and not messagebox.askyesno('Replace transfer results?','Target or settings changed. Export the current transfer first to keep it. Start a new transfer?',parent=win):return
            state.update(identity=session_identity('Transfer '+source_title),records={},signature=signature,units=units,desired=desired,spans=target_layout(raw,mode()),usage={'input_tokens':0,'output_tokens':0},dirty=False,finished=False,error=None)
        elif state['finished']:status.set('This transfer is complete. Change the target or settings to start another.');return
        win.title('Emotional Atlas · '+state['identity']['session_name'])
        state['error']=None;cancel.clear();busy(True);refresh()
        selected_preservation='flexible' if preservation.get()=='Flexible transformation' else 'strict'
        selected_mode=mode();selected_strength=int(strength.get()[:-1])/100;selected_attempts=int(attempts.get());completed=copy.deepcopy(state['records'])
        def worker():
            try:
                for event in run_transfer(source_rows,source_total,raw,selected_mode,key,cancel,provider=provider,model=model,
                                          attempts=selected_attempts,strength=selected_strength,preservation=selected_preservation,completed=completed):events.put(event)
                events.put(('done','Transfer complete. Review meaning and final geometry before using the text.'))
            except Cancelled:events.put(('stopped','Stopped. Completed units retained; Resume continues.'))
            except Exception as e:events.put(('error',str(e) if isinstance(e,AnalysisError) else 'Transfer stopped after an unexpected response. Completed units are retained.'))
        threading.Thread(target=worker,daemon=True).start()
    def stop():
        cancel.set();stop_btn.configure(state='disabled');status.set('Stopping after the current API call (up to 150 seconds). Completed units are retained.')
    def open_target():
        if state['dirty'] and not messagebox.askyesno('Replace target?','Export the current transfer before replacing it. Continue?',parent=win):return
        path=filedialog.askopenfilename(parent=win,filetypes=[('Text files','*.txt')])
        if path:
            try:text=Path(path).read_text(encoding='utf-8-sig')
            except (OSError,UnicodeError) as e:messagebox.showerror('Cannot open text',str(e),parent=win);return
            target.delete('1.0','end');target.insert('1.0',text)
            state.update(records={},signature=None,units=[],desired=[],dirty=False,finished=False);refresh()
    def refresh():
        revised.configure(state='normal');revised.delete('1.0','end');revised.insert('1.0',output());revised.configure(state='disabled')
        desired_rows=[]
        for i,p in enumerate(state['desired'],1):
            record=state['records'].get(i);p=record['desired_point'] if record else p
            desired_rows.append({'id':i,'valence':p[0],'direction':p[1],'intensity':(p[2]+1)/2})
        rows=sorted(state['records'].values(),key=lambda r:r['id'])
        for plot,data in zip(plots,(desired_rows,[r['baseline'] for r in rows],[r.get('final_score',r['score']) for r in rows])):
            plot.rows=data;plot.draw()
        before=[r['before_error'] for r in rows if r['before_error'] is not None]
        after=[r.get('final_error',r['after_error']) for r in rows if r.get('final_error',r['after_error']) is not None]
        fmt=lambda values:f'{sum(values)/len(values):.3f} ({len(values)} scored)' if values else 'unavailable'
        summary.set(f"{len(rows)}/{len(state['units'])} units processed · {sum(r['accepted'] for r in rows)} revisions retained · {sum(bool(r.get('processing_errors')) for r in rows)} units flagged · Mean normalized distance: before {fmt(before)} → after {fmt(after)}. Not a calibrated quality score.")
        if rows:inspect(rows[-1]['id'])
    def inspect(index):
        r=state['records'].get(index)
        if not r:return
        lines=[f'Unit {index}: '+r['fidelity'],f"Requested point: {r['desired_point']}",f"Error before: {r['before_error']}; final/estimated after: {r.get('final_error',r['after_error'])}"]
        for error in r.get('processing_errors',[]):lines.append(f"Flagged — {error['stage']}: {error['message']}")
        if 'final_score' not in r:lines.append('Final assembled-text scoring is not complete.')
        for i,attempt in enumerate(r['attempts'],1):
            lines.extend([f"Attempt {i}: {attempt['changes']}",f"Meaning review: {attempt['meaning_review']}",f"Candidate error: {attempt['error']}", attempt.get('selection_note',''), 'Candidate: '+attempt['text']])
        log.configure(state='normal');log.delete('1.0','end');log.insert('1.0','\n\n'.join(lines));log.configure(state='disabled')
    def save_transfer():
        # Freeze the snapshot before a native save dialog can process queued UI events.
        signature=(target.get('1.0','end-1c'),mode(),strength.get(),attempts.get(),preservation.get())
        records=state['records'];usage=state['usage'];complete=state['finished'];identity=state['identity']
        if signature!=state['signature']:
            if records:
                messagebox.showinfo('Settings changed','Save the existing transfer before changing its text/settings, or start the new transfer first.',parent=win);return
            try:prepare(source_rows,source_total,signature[0],signature[1])
            except AnalysisError as error:messagebox.showerror('Cannot save transfer',str(error),parent=win);return
            records={};usage={'input_tokens':0,'output_tokens':0};complete=False
        data=checkpoint(source_snapshot,signature,records,usage,complete,state['error'],identity)
        path=filedialog.asksaveasfilename(parent=win,defaultextension='.json',initialfile=session_filename(identity,timestamp()),filetypes=[('Transfer checkpoint','*.json')])
        if not path:return
        try:write_checkpoint(path,data)
        except (OSError,ValueError) as error:messagebox.showerror('Save failed',str(error),parent=win);return
        if data['records']=={str(i):r for i,r in state['records'].items()} and data['usage']==state['usage'] and data['complete']==state['finished']:state['dirty']=False
        status.set(f"Transfer saved: {len(data['records'])} completed units. In-flight work is not included; reopening resumes from this checkpoint. API keys are not saved.")

    def save(kind):
        if not state['records']:messagebox.showinfo('No results','Run a transfer first.',parent=win);return
        path=filedialog.asksaveasfilename(parent=win,defaultextension='.'+kind,initialfile='emotional-shape-transfer.'+kind)
        if not path:return
        raw,segmentation,amount,passes,policy=state['signature']
        data={'format':'emotional-atlas-transfer-v1','created_at':datetime.now(timezone.utc).isoformat(),
              'source':{'title':source_title,'segmentation':source_mode,'total_units':source_total,'knots':knots,'provider':provider,'model':model},
              'editing_policy':policy,'target':raw,'target_spans':state['spans'],'segmentation':segmentation,'strength':amount,'max_attempts':passes,'revised_text':output(),
              'flagged_units':[i for i,r in state['records'].items() if r.get('processing_errors')],'records':state['records'],'usage':state['usage'],'complete':state['finished'],'last_error':state['error'],
              'geometry':'p=(valence,direction,2*intensity-1). Source p(t) is piecewise linear on normalized source-unit positions, clamped at endpoints. For one target unit use t=0.5. Desired q=(1-strength)*baseline + strength*p(t); if baseline direction is unavailable, use p(t). Error=Euclidean distance/(2*sqrt(3)). Smoothed display meshes are not used.',
              'limitations':'Meaning checks and emotional scores are model judgments, not guarantees. Geometry and semantic fidelity can conflict; Flexible mode selects the closest reasonable scored revision among attempts even if it does not improve on the original; meaning changes do not veto selection. Strict mode requires preserved meaning and improvement. Originals remain when no candidate qualifies. Final context may change scores. Pending units remain original in partial exports.'}
        try:Path(path).write_text(output() if kind=='txt' else json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        except OSError as e:messagebox.showerror('Export failed',str(e),parent=win);return
        if kind=='json':state['dirty']=False
        status.set('Exported '+Path(path).name+(' (partial: pending units remain original)' if not state['finished'] else ''))
    def poll():
        if state['closed']:return
        changed=False
        try:
            while True:
                kind,value=events.get_nowait()
                if kind=='status':
                    if not cancel.is_set():status.set(value)
                elif kind=='usage':
                    for k in state['usage']:state['usage'][k]+=value.get(k,0)
                elif kind=='unit':state['records'][value['id']]=copy.deepcopy(value);state['dirty']=True;changed=True
                elif kind in ('done','stopped','error'):
                    busy(False);state['finished']=kind=='done';state['error']=value if kind=='error' else None;status.set(value+(f" {sum(bool(r.get('processing_errors')) for r in state['records'].values())} unit(s) flagged in the report." if kind=='done' else ''))
        except queue.Empty:pass
        if changed:refresh()
        win.after(100,poll)
    def close():
        if (state['dirty'] or state['running']) and not messagebox.askyesno('Close transfer?','Unsaved transfer results will be lost. Closing also stops further requests after the current call. Close?',parent=win):return
        cancel.set();state['closed']=True;win.destroy()
    win.protocol('WM_DELETE_WINDOW',close)
    win.transfer_controls={'state':state,'target':target,'revised':revised,'start':start,'stop':stop,'save':save,'save_transfer':save_transfer,'mode':unit_mode,'strength':strength,'attempts':attempts,'preservation':preservation,'plots':plots,'refresh':refresh,'close':close}
    if saved:
        state.update({k:v for k,v in saved.items() if k!='source'})
        raw,segmentation,amount,passes,policy=state['signature']
        target.insert('1.0',raw);unit_mode.set('Sentences' if segmentation=='sentence' else 'Paragraphs')
        strength.set(amount);attempts.set(passes);preservation.set(policy);refresh()
        win.title('Emotional Atlas · '+state['identity']['session_name'])
        status.set(f"Restored {len(state['records'])}/{len(state['units'])} completed units. Enter the {provider} API key in the main window, then Transfer / Resume.")
    poll();return win
