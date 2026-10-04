import os, sys, traceback, glob
print("frozen:", getattr(sys, "frozen", False))
try:
    from webview.platforms import winforms
    print("winforms: OK")
except Exception:
    traceback.print_exc(limit=6)
if getattr(sys, "frozen", False):
    mp = sys._MEIPASS
    for name in ("clr.py", "clr_loader", "pythonnet", "hostfxr", "coreclr"):
        print(f"  {name:<14} {len(glob.glob(os.path.join(mp,'**',name),recursive=True))} Treffer")
