"""DXF exporter using KiCad PLOT_CONTROLLER."""

import os
import pcbnew


def export(board, layer, output_dir):
    """Export the given layer as DXF.

    Sets the auxiliary origin to the board bounding box top-left so that
    DXF coordinates start at (0, 0).  The caller must restore the original
    auxiliary origin (use try/finally).

    Returns:
        (dxf_path, width_mm, height_mm)
    """
    os.makedirs(output_dir, exist_ok=True)

    bbox = board.GetBoardEdgesBoundingBox()
    board.GetDesignSettings().SetAuxOrigin(pcbnew.VECTOR2I(bbox.GetLeft(), bbox.GetTop()))

    pctl = pcbnew.PLOT_CONTROLLER(board)
    popt = pctl.GetPlotOptions()

    popt.SetOutputDirectory(output_dir)
    popt.SetPlotFrameRef(False)
    popt.SetAutoScale(False)
    popt.SetScale(1)
    popt.SetMirror(layer == pcbnew.B_Paste)
    popt.SetUseAuxOrigin(True)
    popt.SetDXFPlotUnits(pcbnew.DXF_UNITS_MM)
    popt.SetDXFPlotPolygonMode(True)

    pctl.SetLayer(layer)
    pctl.OpenPlotfile("paste", pcbnew.PLOT_FORMAT_DXF, "Paste layer")
    pctl.PlotLayer()
    dxf_path = pctl.GetPlotFileName()
    pctl.ClosePlot()

    width_mm  = pcbnew.ToMM(bbox.GetWidth())
    height_mm = pcbnew.ToMM(bbox.GetHeight())
    return dxf_path, width_mm, height_mm
