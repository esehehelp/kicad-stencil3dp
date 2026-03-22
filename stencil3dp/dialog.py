"""Settings dialog for Stencil 3DP plugin."""

import json
import os
import shutil
import wx


PREFS_PATH = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "kicad", "stencil3dp_prefs.json"
)


def _default_openscad_path():
    found = shutil.which("openscad")
    if found:
        return found
    candidates = [
        r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe",
        r"C:\Program Files\OpenSCAD\openscad.exe",
        r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""


DEFAULTS = {
    "layer":           "F.Paste",
    "thickness_mm":    0.16,
    "offset_mm":       -0.05,
    "pin_holes":       True,
    "pin_dia":         1.5,
    "pin_margin":      3.0,
    "warn_fine_pitch": True,
    "output_dir":      "",
    "openscad_path":   _default_openscad_path(),
    "run_openscad":    True,
}


def _load_prefs():
    try:
        with open(PREFS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so new keys are always present
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULTS)


def _save_prefs(cfg):
    try:
        os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


class StencilDialog(wx.Dialog):
    def __init__(self, parent, board_dir=""):
        super().__init__(
            parent, title="Stencil 3DP Settings",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._board_dir = board_dir
        self._prefs = _load_prefs()
        if not self._prefs["output_dir"]:
            self._prefs["output_dir"] = board_dir

        self._build_ui()
        self._load_into_ui()
        self.Fit()
        self.SetMinSize(self.GetSize())

    # ------------------------------------------------------------------
    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        fgs   = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        fgs.AddGrowableCol(1, 1)

        def label(text):
            return wx.StaticText(panel, label=text)

        # Layer
        fgs.Add(label("Layer:"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._layer = wx.Choice(panel, choices=["F.Paste", "B.Paste"])
        fgs.Add(self._layer, flag=wx.EXPAND)

        # Thickness
        fgs.Add(label("Thickness (mm):"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._thickness = wx.TextCtrl(panel, value="")
        fgs.Add(self._thickness, flag=wx.EXPAND)

        # Offset
        fgs.Add(label("Offset (mm):"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._offset = wx.TextCtrl(panel, value="")
        fgs.Add(self._offset, flag=wx.EXPAND)

        # Pin holes checkbox
        fgs.Add(label("Registration pin holes:"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._pin_holes = wx.CheckBox(panel)
        fgs.Add(self._pin_holes)

        # Pin diameter
        fgs.Add(label("Pin diameter (mm):"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._pin_dia = wx.TextCtrl(panel, value="")
        fgs.Add(self._pin_dia, flag=wx.EXPAND)

        # Pin margin
        fgs.Add(label("Pin margin (mm):"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._pin_margin = wx.TextCtrl(panel, value="")
        fgs.Add(self._pin_margin, flag=wx.EXPAND)

        # Fine-pitch warning
        fgs.Add(label("Fine-pitch warning:"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._warn_fine_pitch = wx.CheckBox(panel)
        fgs.Add(self._warn_fine_pitch)

        # Output directory
        fgs.Add(label("Output directory:"), flag=wx.ALIGN_CENTER_VERTICAL)
        outdir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._output_dir = wx.TextCtrl(panel, value="", size=(260, -1))
        btn_browse = wx.Button(panel, label="…", size=(28, -1))
        outdir_sizer.Add(self._output_dir, proportion=1, flag=wx.EXPAND)
        outdir_sizer.Add(btn_browse, flag=wx.LEFT, border=4)
        fgs.Add(outdir_sizer, flag=wx.EXPAND)
        btn_browse.Bind(wx.EVT_BUTTON, self._on_browse_output)

        # OpenSCAD path
        fgs.Add(label("OpenSCAD path:"), flag=wx.ALIGN_CENTER_VERTICAL)
        scad_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._openscad_path = wx.TextCtrl(panel, value="", size=(260, -1))
        btn_scad = wx.Button(panel, label="…", size=(28, -1))
        scad_sizer.Add(self._openscad_path, proportion=1, flag=wx.EXPAND)
        scad_sizer.Add(btn_scad, flag=wx.LEFT, border=4)
        fgs.Add(scad_sizer, flag=wx.EXPAND)
        btn_scad.Bind(wx.EVT_BUTTON, self._on_browse_openscad)

        # Run OpenSCAD
        fgs.Add(label("Run OpenSCAD now:"), flag=wx.ALIGN_CENTER_VERTICAL)
        self._run_openscad = wx.CheckBox(panel)
        fgs.Add(self._run_openscad)

        sizer.Add(fgs, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn     = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        panel.SetSizer(sizer)

        # Connect panel to dialog so Fit() works correctly
        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        dlg_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(dlg_sizer)

    # ------------------------------------------------------------------
    def _load_into_ui(self):
        p = self._prefs
        layers = ["F.Paste", "B.Paste"]
        self._layer.SetSelection(layers.index(p["layer"]) if p["layer"] in layers else 0)
        self._thickness.SetValue(str(p["thickness_mm"]))
        self._offset.SetValue(str(p["offset_mm"]))
        self._pin_holes.SetValue(bool(p["pin_holes"]))
        self._pin_dia.SetValue(str(p["pin_dia"]))
        self._pin_margin.SetValue(str(p["pin_margin"]))
        self._warn_fine_pitch.SetValue(bool(p["warn_fine_pitch"]))
        self._output_dir.SetValue(p["output_dir"])
        self._openscad_path.SetValue(p["openscad_path"])
        self._run_openscad.SetValue(bool(p["run_openscad"]))

    # ------------------------------------------------------------------
    def _on_browse_output(self, _evt):
        dlg = wx.DirDialog(self, "Select output directory",
                           defaultPath=self._output_dir.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
            self._output_dir.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_browse_openscad(self, _evt):
        dlg = wx.FileDialog(
            self, "Locate openscad executable",
            wildcard="Executables (*.exe)|*.exe|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        if dlg.ShowModal() == wx.ID_OK:
            self._openscad_path.SetValue(dlg.GetPath())
        dlg.Destroy()

    # ------------------------------------------------------------------
    def _on_ok(self, evt):
        try:
            cfg = self._collect()
        except ValueError as e:
            wx.MessageBox(str(e), "Invalid input", wx.OK | wx.ICON_ERROR)
            return
        _save_prefs(cfg)
        self._cfg = cfg
        evt.Skip()  # allow dialog to close with ID_OK

    def _collect(self):
        def _float(ctrl, name):
            try:
                return float(ctrl.GetValue())
            except ValueError:
                raise ValueError(f"'{name}' must be a number.")

        layers = ["F.Paste", "B.Paste"]
        return {
            "layer":           layers[self._layer.GetSelection()],
            "thickness_mm":    _float(self._thickness, "Thickness"),
            "offset_mm":       _float(self._offset, "Offset"),
            "pin_holes":       self._pin_holes.GetValue(),
            "pin_dia":         _float(self._pin_dia, "Pin diameter"),
            "pin_margin":      _float(self._pin_margin, "Pin margin"),
            "warn_fine_pitch": self._warn_fine_pitch.GetValue(),
            "output_dir":      self._output_dir.GetValue() or self._board_dir,
            "openscad_path":   self._openscad_path.GetValue(),
            "run_openscad":    self._run_openscad.GetValue(),
        }

    def GetConfig(self):
        return self._cfg
