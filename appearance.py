"""Monochrome interface palette; data and chosen surface colors are unchanged."""
LIGHT={
    '#111113':'#ffffff', '#19191c':'#f5f5f7', '#f2f2f3':'#202024',
    '#aaaab0':'#60606a', '#3d3d43':'#ccccd2', '#303035':'#ddddE3',
    '#55555d':'#92929a', '#3b3b43':'#d0d0d8', '#2d2d33':'#e8e8ed',
    '#75757d':'#85858d', '#35353d':'#e0e0e6', '#484851':'#c0c0ca',
    '#41414a':'#d6d6df', '#2b2b31':'#eeeef2', '#3c3c46':'#d8d8e3',
    '#44444e':'#dadae5', '#666666':'#777777',
}
LIGHT={k:v.lower() for k,v in LIGHT.items()}
light=False

def ui_color(dark):
    return LIGHT.get(dark.lower(),dark) if light else dark

def set_light(enabled):
    global light
    light=bool(enabled)

def recolor_widgets(root,was_light):
    previous={v:k for k,v in LIGHT.items()} if was_light else {k:k for k in LIGHT}
    def converted(value):
        value=str(value).lower()
        return ui_color(previous[value]) if value in previous else None
    def visit(widget):
        for option in ('background','foreground','insertbackground','selectbackground','selectforeground','highlightbackground','highlightcolor','disabledforeground','activebackground','activeforeground'):
            if option in widget.keys():
                value=converted(widget.cget(option))
                if value is not None:widget.configure(**{option:value})
        # Evidence and selection tags have their own colors.
        import tkinter as tk
        if isinstance(widget,tk.Text):
            for tag in widget.tag_names():
                for option in ('background','foreground'):
                    value=converted(widget.tag_cget(tag,option))
                    if value is not None:widget.tag_configure(tag,**{option:value})
        for child in widget.winfo_children():visit(child)
        if isinstance(widget,tk.Canvas) and hasattr(widget,'draw'):widget.draw()
    visit(root)
