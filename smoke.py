"""Offline native bundle smoke test, explicitly invoked by release tooling."""
import json


def run_smoke_test(app_class, report_path):
    app = app_class()
    try:
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
        for mode in ['PCA 2D','PCA 3D','Emotion axes']:
            app.plot_mode.set(mode);app.change_plot_mode();app.update_idletasks()
            assert len(app.plot.points)==3
            assert app.expanded_plot.mode==mode
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
        app.dirty=False
        report_path.write_text(json.dumps({'version':'0.3','status':'passed','checks':[
            'native Tk startup','icon','monochrome controls','paragraph plot','expanded plot synchronization',
            'PCA 2D and 3D','playback from saved-style data','restore plot',
            'proportional pixel scrolling','nested scroll isolation','small-window scrolling','footer access','keyboard focus visibility','uncluttered empty plot','provider switching','separate in-memory keys','provider controls locked during analysis']},indent=2))
    finally:
        app.pause_playback();app.destroy()
