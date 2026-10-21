# Natron 2.5 (After Effects / Nuke compositing alternative)

- Headless exe: `NatronRenderer` (GUI: `Natron`). Licence GPL-2.0; portable archive from the official releases.
- CPU render works without a GPU; still take a resource snapshot (and the GPU lock if the graph uses GPU plug-ins) for big jobs.

## Verified (Natron 2.5.0, Windows): render a graph built in Python (exit 0, ~5 s)
```
set NATRON_OUT=/path/out/natron_w_###.png
NatronRenderer -w Write1 1-1 /path/natron_graph.py
```
`natron_graph.py` (project-as-script; Natron calls `createInstance`):
```python
import os
def createInstance(app, group):
    bg = app.createNode("net.sf.openfx.CheckerBoardPlugin", -1, group)
    txt = app.createNode("net.fxarena.openfx.Text", -1, group)
    txt.getParam("text").setValue("Natron -w render")
    m = app.createNode("net.sf.openfx.MergePlugin", -1, group)   # input 0 = B, 1 = A
    m.connectInput(0, bg); m.connectInput(1, txt)
    w = app.createNode("fr.inria.openfx.WriteOIIO", -1, group)
    w.setScriptName("Write1")
    w.getParam("filename").setValue(os.environ.get("NATRON_OUT", "natron_w_###.png"))
    w.connectInput(0, m)
```
Result: a 1920×1080 PNG, checkerboard with text. `.ntp` projects render the same way:
`NatronRenderer -w <WriteNode> <first-last> project.ntp`.
For footage use `fr.inria.openfx.ReadOIIO` (images) or `fr.inria.openfx.ReadFFmpeg` (video) and set `filename`.

## Caveats
- `--version` prints the version but exits 1.
- `-t script.py` (interpreter mode, `app1.render(w,1,1)`): the frame is written, then the process crashes on exit
  (0xC0000005) — **not verified**, use `-w`.
- Natron re-reads the script as text: no backslashes anywhere in the `.py`; pass paths via env vars with forward slashes.
- The Text node does not composite over its input — use a Merge node.
