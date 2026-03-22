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
        from . import scad_generator
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

        # Generate SCAD directly from pad geometry (no DXF needed)
        scad_path, w, h = scad_generator.generate(board, layer, cfg, output_dir)
        stl_path = os.path.splitext(scad_path)[0] + ".stl"

        runner = OpenScadRunner(cfg.get("openscad_path") or None)
        try:
            runner.render(scad_path, stl_path)
            msg = f"Stencil generated:\n\nSCAD: {scad_path}\nSTL:  {stl_path}"
        except FileNotFoundError:
            msg = (
                f"OpenSCAD not found at: {runner.openscad_path}\n\n"
                f"SCAD saved to: {scad_path}\n\n"
                f"Run manually:\n"
                f"openscad --render -o \"{stl_path}\" \"{scad_path}\""
            )
        except subprocess.CalledProcessError as e:
            msg = (
                f"OpenSCAD failed (exit {e.returncode}):\n{e.stderr}\n\n"
                f"SCAD saved to: {scad_path}"
            )

        wx.MessageBox(msg, "Stencil 3DP", wx.OK | wx.ICON_INFORMATION)
