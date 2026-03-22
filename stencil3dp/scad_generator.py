"""Generate self-contained OpenSCAD stencil file from KiCad pad geometry."""

import os

import pcbnew


def _paste_size_mm(pad, fp, board):
    """Return (pw_mm, ph_mm) of the actual paste aperture, applying paste margins.

    Mirrors PLOT_CONTROLLER behaviour: pad margin → footprint margin → board margin.
    Returns (None, None) if the effective aperture vanishes (margin too negative).
    Falls back to raw copper pad size if any API call fails.
    """
    try:
        def _margin():
            for getter in (pad.GetLocalSolderPasteMargin,
                           fp.GetLocalSolderPasteMargin):
                try:
                    v = int(getter())
                    if v != 0:
                        return pcbnew.ToMM(v)
                except Exception:
                    pass
            try:
                ds = board.GetDesignSettings()
                for attr in ("m_SolderPasteMargin", "GetSolderPasteMargin"):
                    if hasattr(ds, attr):
                        raw = getattr(ds, attr)
                        v = raw() if callable(raw) else raw
                        return float(pcbnew.ToMM(int(v)))
            except Exception:
                pass
            return 0.0

        def _ratio():
            for getter in (pad.GetLocalSolderPasteMarginRatio,
                           fp.GetLocalSolderPasteMarginRatio):
                try:
                    v = float(getter())
                    if v != 0.0:
                        return v
                except Exception:
                    pass
            try:
                ds = board.GetDesignSettings()
                for attr in ("m_SolderPasteMarginRatio", "GetSolderPasteMarginRatio"):
                    if hasattr(ds, attr):
                        raw = getattr(ds, attr)
                        return float(raw() if callable(raw) else raw)
            except Exception:
                pass
            return 0.0

        margin = float(_margin())
        ratio  = float(_ratio())
        size   = pad.GetSize()
        pw_cu  = float(pcbnew.ToMM(size.x))
        ph_cu  = float(pcbnew.ToMM(size.y))

        pw = pw_cu + 2.0 * (margin + ratio * pw_cu)
        ph = ph_cu + 2.0 * (margin + ratio * ph_cu)

        if pw <= 0 or ph <= 0:
            return None, None
        return pw, ph

    except Exception:
        # Fallback: use raw copper pad size
        size  = pad.GetSize()
        pw_cu = float(pcbnew.ToMM(size.x))
        ph_cu = float(pcbnew.ToMM(size.y))
        return pw_cu, ph_cu


def _get_angle_deg(pad):
    try:
        return pad.GetOrientation().AsDegrees()
    except AttributeError:
        return pad.GetOrientation() / 10.0


def _pad_scad(x, y, pw, ph, angle, shape, pad, offset):
    """Return OpenSCAD 2D snippet for one pad aperture (already in mm, Y-flipped)."""
    # Negate angle because we flipped Y axis
    a = -angle

    if shape in (pcbnew.PAD_SHAPE_CIRCLE,):
        d = max(pw, ph) + 2 * offset
        d = max(d, 0.01)
        return f"translate([{x:.4f},{y:.4f}]) circle(d={d:.4f},$fn=32);"

    elif shape in (pcbnew.PAD_SHAPE_OVAL,):
        if pw >= ph:
            dx = (pw - ph) / 2
            cr = ph / 2 + offset
            rot = a
        else:
            dx = (ph - pw) / 2
            cr = pw / 2 + offset
            rot = a + 90
        cr = max(cr, 0.01)
        return (
            f"translate([{x:.4f},{y:.4f}]) rotate([0,0,{rot:.4f}])\n"
            f"  hull(){{\n"
            f"    translate([{dx:.4f},0]) circle(r={cr:.4f},$fn=32);\n"
            f"    translate([{-dx:.4f},0]) circle(r={cr:.4f},$fn=32);\n"
            f"  }}"
        )

    elif shape in (pcbnew.PAD_SHAPE_ROUNDRECT,):
        try:
            rr = pcbnew.ToMM(pad.GetRoundRectCornerRadius())
        except Exception:
            rr = min(pw, ph) * pad.GetRoundRectRadiusRatio() / 2
        ew = pw - 2 * rr
        eh = ph - 2 * rr
        total_r = max(rr + offset, 0.01)
        # If either inner dimension is zero or negative the pad is stadium-shaped;
        # fall back to the hull-of-two-circles approach to avoid degenerate geometry.
        if ew <= 0 and eh <= 0:
            # Fully circular
            return f"translate([{x:.4f},{y:.4f}]) circle(r={total_r:.4f},$fn=32);"
        elif ew <= 0:
            # Stadium along Y axis
            dy = eh / 2
            return (
                f"translate([{x:.4f},{y:.4f}]) rotate([0,0,{a:.4f}])\n"
                f"  hull(){{\n"
                f"    translate([0,{dy:.4f}]) circle(r={total_r:.4f},$fn=32);\n"
                f"    translate([0,{-dy:.4f}]) circle(r={total_r:.4f},$fn=32);\n"
                f"  }}"
            )
        elif eh <= 0:
            # Stadium along X axis
            dx = ew / 2
            return (
                f"translate([{x:.4f},{y:.4f}]) rotate([0,0,{a:.4f}])\n"
                f"  hull(){{\n"
                f"    translate([{dx:.4f},0]) circle(r={total_r:.4f},$fn=32);\n"
                f"    translate([{-dx:.4f},0]) circle(r={total_r:.4f},$fn=32);\n"
                f"  }}"
            )
        else:
            return (
                f"translate([{x:.4f},{y:.4f}]) rotate([0,0,{a:.4f}])\n"
                f"  offset(r={total_r:.4f},$fn=32) square([{ew:.4f},{eh:.4f}],center=true);"
            )

    else:
        # RECT, TRAPEZOID, CHAMFERED_RECT, CUSTOM → bounding rectangle
        ew = max(pw + 2 * offset, 0.01)
        eh = max(ph + 2 * offset, 0.01)
        return (
            f"translate([{x:.4f},{y:.4f}]) rotate([0,0,{a:.4f}])\n"
            f"  square([{ew:.4f},{eh:.4f}],center=true);"
        )


def generate(board, layer, cfg, output_dir):
    """Generate a self-contained .scad stencil file.

    Returns:
        (scad_path, w_mm, h_mm)
    """
    os.makedirs(output_dir, exist_ok=True)

    bbox   = board.GetBoardEdgesBoundingBox()
    ox     = bbox.GetLeft()
    oy     = bbox.GetTop()
    w_mm   = pcbnew.ToMM(bbox.GetWidth())
    h_mm   = pcbnew.ToMM(bbox.GetHeight())

    thickness = cfg["thickness_mm"]
    offset    = cfg["offset_mm"]
    margin    = cfg.get("margin_mm", 10.0)
    mirror    = (layer == pcbnew.B_Paste)

    pad_snippets = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.IsOnLayer(layer):
                continue
            pos  = pad.GetPosition()
            x_mm = pcbnew.ToMM(pos.x - ox)
            # KiCad Y-down → OpenSCAD Y-up
            y_mm = h_mm - pcbnew.ToMM(pos.y - oy)

            if mirror:
                x_mm = w_mm - x_mm

            # Use paste-margin-adjusted size (mirrors PLOT_CONTROLLER behaviour)
            pw, ph = _paste_size_mm(pad, fp, board)
            if pw is None:
                continue  # paste margin makes aperture vanish; skip

            angle = _get_angle_deg(pad)

            snippet = _pad_scad(
                x_mm + margin, y_mm + margin,
                pw, ph, angle,
                pad.GetShape(), pad, offset
            )
            pad_snippets.append("    " + snippet)

    apertures = "\n".join(pad_snippets) if pad_snippets else "    // no pads found"

    # Registration pin holes in the margin corners (outside board area)
    pin_lines = []
    if cfg.get("pin_holes") and cfg.get("pin_dia", 0) > 0:
        pd  = cfg["pin_dia"]
        hm  = margin / 2   # center of each corner margin region
        corners = [
            (hm,                   hm),
            (w_mm + margin + hm,   hm),
            (hm,                   h_mm + margin + hm),
            (w_mm + margin + hm,   h_mm + margin + hm),
        ]
        for cx, cy in corners:
            pin_lines.append(
                f"    translate([{cx:.4f},{cy:.4f},-0.01])\n"
                f"        cylinder(h={thickness+0.02:.4f},d={pd},$fn=32);"
            )

    pin_block = "\n".join(pin_lines)

    scad = f"""\
// Stencil 3DP - auto-generated by KiCad plugin
// Board: {w_mm:.2f} x {h_mm:.2f} mm   margin: {margin} mm
// Layer: {"B.Paste (mirrored)" if mirror else "F.Paste"}

thickness = {thickness};
margin    = {margin};
board_w   = {w_mm:.4f};
board_h   = {h_mm:.4f};

difference() {{
    // Stencil plate (board + margin on all sides)
    linear_extrude(height = thickness)
        square([board_w + 2*margin, board_h + 2*margin]);

    // Paste apertures
    translate([0, 0, -0.01])
    linear_extrude(height = thickness + 0.02)
    union() {{
{apertures}
    }}

    // Registration pin holes (centered in margin corners)
{pin_block}
}}
"""

    board_name = os.path.splitext(os.path.basename(board.GetFileName()))[0] or "stencil"
    scad_path  = os.path.join(output_dir, f"{board_name}-stencil.scad")
    with open(scad_path, "w", encoding="utf-8") as f:
        f.write(scad)

    return scad_path, w_mm, h_mm
