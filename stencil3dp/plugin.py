"""KiCad ActionPlugin: Stencil 3DP."""

import os
import subprocess
import pcbnew
import wx


LAYER_MAP = {
    "F.Paste": pcbnew.F_Paste,
    "B.Paste": pcbnew.B_Paste,
}


def detect_fine_pitch(board, layer, threshold_mm=0.5):
    """Return list of (reference, distance_mm) for close pad pairs on layer."""
    results = []
    for fp in board.GetFootprints():
        pads = [p for p in fp.Pads() if p.IsOnLayer(layer)]
        if len(pads) < 2:
            continue
        for i, p1 in enumerate(pads):
            for p2 in pads[i + 1:]:
                dist = pcbnew.ToMM(
                    (p1.GetPosition() - p2.GetPosition()).EuclideanNorm()
                )
                if dist < threshold_mm:
                    results.append((fp.GetReference(), round(dist, 3)))
    return results


class StencilPlugin(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Stencil 3DP"
        self.category = "Manufacturing"
        self.description = (
            "Generate a 3D-printable solder paste stencil (STL) "
            "from the F.Paste / B.Paste layer via OpenSCAD."
        )
        self.show_toolbar_button = True

    def Run(self):
        board = pcbnew.GetBoard()
        board_path = board.GetFileName()
        board_dir  = os.path.dirname(board_path) if board_path else os.getcwd()

        # Lazy import to keep startup fast
        from .dialog import StencilDialog
        from . import dxf_exporter
        from .openscad_runner import OpenScadRunner

        dlg = StencilDialog(None, board_dir=board_dir)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        cfg = dlg.GetConfig()
        dlg.Destroy()

        layer     = LAYER_MAP[cfg["layer"]]
        output_dir = cfg["output_dir"]

        # Fine-pitch warning
        if cfg.get("warn_fine_pitch"):
            fine = detect_fine_pitch(board, layer, threshold_mm=0.5)
            if fine:
                refs = ", ".join(f"{r}({d}mm)" for r, d in fine[:10])
                msg = (
                    f"Fine-pitch pads detected (< 0.5 mm apart):\n{refs}\n\n"
                    "Continue generating stencil?"
                )
                dlg2 = wx.MessageDialog(
                    None, msg, "Fine-pitch Warning",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
                )
                proceed = dlg2.ShowModal() == wx.ID_YES
                dlg2.Destroy()
                if not proceed:
                    return

        # DXF export (restore aux origin in finally)
        orig_aux = board.GetAuxOrigin()
        try:
            dxf_path, w, h = dxf_exporter.export(board, layer, output_dir)
        finally:
            board.SetAuxOrigin(orig_aux)

        # OpenSCAD rendering
        stl_path = os.path.splitext(dxf_path)[0] + ".stl"
        scad_path = os.path.join(os.path.dirname(__file__), "..", "gen_stl.scad")
        scad_path = os.path.normpath(scad_path)

        if cfg.get("run_openscad"):
            runner = OpenScadRunner(cfg.get("openscad_path") or None)
            try:
                runner.render(
                    scad_path, dxf_path, stl_path,
                    width=w, height=h,
                    thickness=cfg["thickness_mm"],
                    offset=cfg["offset_mm"],
                    pin_dia=cfg["pin_dia"] if cfg["pin_holes"] else 0,
                    pin_margin=cfg.get("pin_margin", 3.0),
                )
                msg = f"Stencil generated:\n\nDXF: {dxf_path}\nSTL: {stl_path}"
            except FileNotFoundError:
                msg = (
                    f"OpenSCAD not found at: {runner.openscad_path}\n\n"
                    f"DXF saved to: {dxf_path}\n\n"
                    f"Run manually:\n"
                    f"openscad -D 'source=\"{dxf_path}\"' "
                    f"-D 'width={w}' -D 'height={h}' "
                    f"-D 'thickness={cfg['thickness_mm']}' "
                    f"-D 'offset={cfg['offset_mm']}' "
                    f"-o \"{stl_path}\" \"{scad_path}\""
                )
            except subprocess.CalledProcessError as e:
                msg = (
                    f"OpenSCAD failed (exit {e.returncode}):\n{e.stderr}\n\n"
                    f"DXF saved to: {dxf_path}"
                )
        else:
            msg = f"DXF saved to:\n{dxf_path}"

        wx.MessageBox(msg, "Stencil 3DP", wx.OK | wx.ICON_INFORMATION)
