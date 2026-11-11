"""Offline native bundle smoke test, explicitly invoked by release tooling."""
import json


def run_smoke_test(app_class, report_path):
    app = app_class()
    try:
        assert not app.sentence_mode.get()
        app.sentence_mode.set(True);app.set_source('I was sad. Then I felt relieved!','Sentence fixture')
        assert app.paragraphs==['I was sad.','Then I felt relieved!'] and app.mode_used=='sentence'
        assert 'sentences' in app.stats.get()
        from unittest.mock import patch
        temporary_session=report_path.parent/'sentence-session-smoke.json'
        with patch('tkinter.filedialog.asksaveasfilename',return_value=str(temporary_session)):app.save_session()
        app.sentence_mode.set(False)
        with patch('tkinter.filedialog.askopenfilename',return_value=str(temporary_session)):app.open_session()
        assert app.sentence_mode.get() and app.mode_used=='sentence' and len(app.paragraphs)==2
        temporary_session.unlink()
        app.sentence_mode.set(False)
        app.api_keys['openai'].set('offline-openai-key')
        app.provider.set('VT ARC');app.update_provider();app.update()
        assert app.key.get()=='' and app.arc_model_row.winfo_ismapped()
        app.key.set('offline-arc-key')
        app.provider.set('OpenAI');app.update_provider();app.update()
        assert app.key.get()=='offline-openai-key' and not app.arc_model_row.winfo_ismapped()
        app.provider.set('VT ARC');app.update_provider();app.update()
        assert app.key.get()=='offline-arc-key'
        app.set_running(True)
        assert str(app.provider_box.cget('state'))=='disabled'
        assert str(app.arc_model_box.cget('state'))=='disabled'
        app.set_running(False)
        app.set_source('First paragraph.\n\nSecond paragraph.\n\nThird paragraph.', 'Synthetic release smoke test')
        app.results = {i: {'id': i, 'intensity': .2*i, 'valence': (i-2)*.6,
            'direction': -.8 if i==1 else .3*i, 'direction_status': 'inward' if i==1 else 'outward',
            'tone': 'negative' if i==1 else 'positive', 'uncertainty': 'low', 'summary': 'Synthetic fixture; not model inference.',
            'uncertainty_note': '', 'emotions': []} for i in (1,2,3)}
        app.refresh();app.update_idletasks()
        assert len(app.plot.points)==3
        assert app.app_icon.width()>0
        app.toggle_expanded_plot();app.update_idletasks()
        assert len(app.expanded_plot.points)==3
        original_paragraph=app.paragraphs[0]
        app.paragraphs[0]='A long paragraph for the expanded view. '*100
        app.current_id=1;app.plot.selected=1;app.sync_expanded_plot();app.update()
        assert app.paragraphs[0] in app.expanded_text.get('1.0','end')
        before_height=app.expanded_text.winfo_height()
        app.toggle_expanded_text();app.update()
        assert app.expanded_text.winfo_height()>before_height
        app.expanded_text.yview_moveto(1);app.update()
        position=app.expanded_text.yview()
        app.plot.rotate(.1,0);app.update()
        assert app.expanded_text.yview()==position
        app.toggle_expanded_text();app.update()
        app.paragraphs[0]=original_paragraph;app.sync_expanded_plot()

        for mode in ['PCA 2D','PCA 3D','Emotion axes']:
            app.plot_mode.set(mode);app.change_plot_mode();app.update_idletasks()
            assert len(app.plot.points)==3
            assert app.expanded_plot.mode==mode
        entry=next(r for r in app.lexicon if r['phrase']=='get your goat')
        app.idiom_results={1:{'provider':'openai','model':'offline fixture','matches':[{
            'idiom_id':entry['id'],'kind':'imagery','quote':'First paragraph.',
            'explanation':'Synthetic rendering fixture only.','alternative':'No actual inference.', 'entry':entry}]}}
        app.current_id=1;app.refresh();app.update_idletasks()
        assert app.plot.idiom_ids=={1} and app.expanded_plot.idiom_ids=={1}
        assert any(app.plot.itemcget(item,'fill')=='#f1d76a' for item in app.plot.find_all() if app.plot.type(item)=='oval')
        assert 'Possible dream / imagery echo' in app.detail.get('1.0','end')
        app.filter.set('Idiom candidates');app.refresh()
        assert app.tree.get_children()==('1',)
        app.filter.set('All segments');app.refresh()
        app.toggle_playback();app.playback_tick();app.pause_playback()
        assert app.timeline.position==1
        assert len(app.plot.points)==1 and len(app.expanded_plot.points)==1
        app.close_expanded_plot()
        assert app.expanded_window is None
        assert not hasattr(app,'book_btn')
        app.geometry('1030x720');app.update()
        canvas=app.workspace_canvas
        assert app.workspace.winfo_height()>canvas.winfo_height()
        canvas.yview_moveto(1);app.update()
        assert canvas.yview()[1]>.999
        assert app.progress.winfo_rooty()+app.progress.winfo_height() <= canvas.winfo_rooty()+canvas.winfo_height()
        canvas.yview_moveto(0);app.update()
        from types import SimpleNamespace
        def wheel(delta,widget=None):
            return app.scroll_workspace(SimpleNamespace(widget=widget or app.workspace,num=None,delta=delta))
        # Small trackpad deltas move pixels, not a tenth of the window.
        wheel(-1);app.update()
        first=canvas.canvasy(0)
        assert 0<=first<=3
        wheel(-5);app.update()
        assert first<canvas.canvasy(0)<=15
        before=canvas.yview()
        wheel(-120,app.source);wheel(-120,app.plot)
        assert canvas.yview()==before  # Preserve text scrolling and plot zoom.
        wheel(0)
        assert canvas.yview()==before
        canvas.yview_moveto(0);app.update()
        app.load_btn.focus_force();app.update()
        assert app.load_btn.winfo_rooty()>=canvas.winfo_rooty()
        assert app.load_btn.winfo_rooty()+app.load_btn.winfo_height() <= canvas.winfo_rooty()+canvas.winfo_height()
        app.plot.rows=[];app.plot.draw()
        assert len(app.plot.find_all())==1  # A single prompt, no placeholder cube.
        # Exercise actual threaded geometry, rendering, evolution and exports.
        import time
        from unittest.mock import patch
        from pathlib import Path
        fixture=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        app.set_source('\n\n'.join(f'Object paragraph {i}.' for i in range(1,9)),'Object fixture')
        app.results={i:{'id':i,'valence':x,'direction':y,'intensity':(z+1)/2,
            'direction_status':'outward' if y>0 else 'inward','tone':'mixed','uncertainty':'low',
            'summary':'Synthetic fixture','uncertainty_note':'','emotions':[]} for i,(x,y,z) in enumerate(fixture,1)}
        app.refresh();original=list(app.plot.rows)
        object_win=app.open_object_view();c=object_win.object_controls
        def wait_object(export=False):
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                app.update()
                if not c['state']['busy'] and not c['state']['pending'] and (not export or not c['state']['exporting']):return
                time.sleep(.02)
            raise AssertionError('Object operation timed out')
        wait_object()
        assert abs(c['state']['model']['volume']-8)<1e-8
        app.update();fixed_height=c['plot'].winfo_height();fixed_sash=c['panes'].sash_coord(0)
        for message in ('', 'Building…', 'Snapshot details '*150):
            c['status'].set(message);app.update()
            assert c['plot'].winfo_height()==fixed_height
            assert c['panes'].sash_coord(0)==fixed_sash
        c['expand_details']();app.update()
        assert c['plot'].winfo_height()<fixed_height
        c['expand_details']();app.update()
        c['evolution'].set('Cumulative')
        for paragraph in (1,4,8):
            c['frame'].set(paragraph);c['changed']();wait_object();app.update()
            if paragraph==1:animation_height=c['plot'].winfo_height()
            else:assert c['plot'].winfo_height()==animation_height

        assert len(c['plot'].find_withtag('object_axis_label'))==3
        assert any('Valence' in c['plot'].itemcget(i,'text') for i in c['plot'].find_withtag('object_axis_label'))
        c['axes'].set(False);c['plot'].draw();assert not c['plot'].find_withtag('object_axis_label')
        c['axes'].set(True);c['plot'].draw()
        assert len(c['plot'].find_all())>1 and app.plot.rows==original
        c['evolution'].set('Moving window');c['window'].set('4');c['frame'].set(8);c['changed']();wait_object()
        assert c['state']['model']['paragraph_ids']==[5,6,7,8]
        c['method'].set('Text-order tube');c['size'].set('.1');c['changed']();wait_object()
        assert c['state']['model']['faces'] and c['state']['model']['closed_edge_manifold']
        c['coordinates'].set('PCA 3D');c['changed']();wait_object()
        assert any('PC1' in c['plot'].itemcget(i,'text') for i in c['plot'].find_withtag('object_axis_label'))
        assert c['state']['model']['faces']
        c['method'].set('Outermost points');c['coordinates'].set('Emotion axes');c['evolution'].set('Cumulative');c['changed']();wait_object()
        c['smoothing'].set('Curved · 2');c['changed']();wait_object()
        assert len(c['state']['model']['faces'])==192
        with patch('object_view.colorchooser.askcolor',return_value=((255,0,0),'#ff0000')):c['choose_color']()
        wait_object()
        assert c['state']['meta']['surface_color']=='#ff0000'
        polygon_colors=[c['plot'].itemcget(item,'fill') for item in c['plot'].find_all() if c['plot'].type(item)=='polygon']
        assert polygon_colors and all(color.endswith('0000') for color in polygon_colors)
        for kind in ('obj','txt','json','evolution'):
            target_path=report_path.parent/('object-smoke.'+('json' if kind=='evolution' else kind))
            with patch('object_view.filedialog.asksaveasfilename',return_value=str(target_path)):c['export'](kind)
            wait_object(export=True)
            assert target_path.exists()
            if kind=='evolution':
                data=json.loads(target_path.read_text());assert len(data['frames'])==8
                assert data['format']=='emotional-atlas-evolution-v2'
                assert 'mesh' not in data['frames'][-1] and len(data['source_samples'])==8
            if kind=='obj':
                material=target_path.with_suffix('.mtl')
                assert 'Kd 1.00000000 0.00000000 0.00000000' in material.read_text()
                material.unlink()
            target_path.unlink()
        c['close']();app.update()
        transfer=app.open_shape_transfer();tc=transfer.transfer_controls
        tc['target'].insert('1.0','The door was open.')
        # Synthetic event stream: tests UI/thread/export plumbing, not LLM quality.
        from shape_transfer import prepare
        source_snapshot=list(app.results.values())
        def fake_transfer(*args,**kwargs):
            units,knots,goals=prepare(source_snapshot,len(app.paragraphs),'The door was open.','blank')
            baseline=dict(app.results[1]);baseline['id']=1
            result={'id':1,'original':units[0],'text':'The door stood open.','source_point':goals[0],
                    'desired_point':goals[0],'baseline':baseline,'score':baseline,'final_score':baseline,
                    'before_error':.5,'after_error':.2,'final_error':.2,'accepted':True,
                    'fidelity':'offline fixture','attempts':[]}
            yield 'usage',{'input_tokens':1,'output_tokens':1}
            yield 'unit',result
        app.api_keys[app.session_provider].set('offline-transfer-key')
        with patch('transfer_view.run_transfer',side_effect=fake_transfer):
            tc['start']()
            deadline=time.monotonic()+10
            while tc['state']['running'] and time.monotonic()<deadline:app.update();time.sleep(.02)
        assert tc['state']['finished'] and 'stood' in tc['revised'].get('1.0','end')
        assert app.results=={r['id']:r for r in source_snapshot}
        for kind in ('txt','json'):
            transfer_path=report_path.parent/('transfer-smoke.'+kind)
            with patch('transfer_view.filedialog.asksaveasfilename',return_value=str(transfer_path)):tc['save'](kind)
            content=transfer_path.read_text();assert 'stood' in content and 'offline-transfer-key' not in content
            if kind=='json':assert json.loads(content)['complete']
            transfer_path.unlink()
        checkpoint_path=report_path.parent/'transfer-checkpoint-smoke.json'
        with patch('transfer_view.filedialog.asksaveasfilename',return_value=str(checkpoint_path)):tc['save_transfer']()
        saved_data=json.loads(checkpoint_path.read_text());assert 'offline-transfer-key' not in checkpoint_path.read_text()
        previous_results=app.results;app.results={}
        with patch('transfer_view.filedialog.askopenfilename',return_value=str(checkpoint_path)):restored_window=app.open_saved_transfer()
        restored_controls=restored_window.transfer_controls
        assert restored_controls['state']['records']==tc['state']['records']
        assert restored_controls['state']['finished'] and 'stood' in restored_controls['revised'].get('1.0','end')
        restored_controls['close']();app.results=previous_results;checkpoint_path.unlink()
        tc['close']();app.update()
        app.dirty=False
        report_path.write_text(json.dumps({'version':(__import__('pathlib').Path(__file__).parent/'VERSION').read_text().strip(),'status':'passed','checks':[
            'transfer checkpoint save/reopen without active source', 'shape-transfer workspace and exports (offline fixture)', 'opt-in sentence analysis and session roundtrip', 'stable animation footer and expandable details', 'labeled object axes and PCA axis switching', 'curved subdivision and single surface color', 'OBJ color material', 'solid geometry and rendering', 'evolution windows', 'OBJ and mathematical exports', 'PCA object coordinates', 'main scatter preserved', 'native Tk startup', 'idiom yellow markers and expanded view', 'idiom evidence and filtering','icon','monochrome controls','paragraph plot','expanded plot synchronization',
            'PCA 2D and 3D','playback from saved-style data','restore plot', 'resizable expanded paragraph and retained scroll position',
            'proportional pixel scrolling','nested scroll isolation','small-window scrolling','footer access','keyboard focus visibility','uncluttered empty plot','provider switching','separate in-memory keys','provider controls locked during analysis']},indent=2))
    finally:
        app.pause_playback();app.destroy()
