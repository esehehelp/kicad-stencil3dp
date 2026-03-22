// KiCad Stencil 3DP - OpenSCAD stencil generator
// Compatible with DXF2STENCIL workflow
// Parameters can be overridden with: openscad -D 'param=value'

source    = "paste.dxf";  // path to F.Paste DXF
width     = 100;           // mm board width
height    = 80;            // mm board height
thickness = 0.16;          // mm stencil thickness
offset    = -0.05;         // mm aperture expansion (positive=expand, negative=shrink)
margin    = 10.0;          // mm border around board edge (for tape/handling)

// Registration pin holes (set pin_dia=0 to disable)
pin_dia    = 1.5;  // mm pin hole diameter
pin_margin = 3.0;  // mm offset from board edge (inside margin)

module pin_holes() {
    if (pin_dia > 0) {
        positions = [
            [margin + pin_margin,              margin + pin_margin],
            [margin + width - pin_margin,      margin + pin_margin],
            [margin + pin_margin,              margin + height - pin_margin],
            [margin + width - pin_margin,      margin + height - pin_margin]
        ];
        for (p = positions)
            translate([p[0], p[1], -0.01])
                cylinder(h = thickness + 0.02, d = pin_dia, $fn = 32);
    }
}

difference() {
    // Stencil base plate: board area + surrounding margin for tape/handling
    linear_extrude(height = thickness)
        square([width + 2*margin, height + 2*margin]);

    // Paste apertures: DXF origin=(0,0) maps to board top-left inside margin
    translate([margin, margin, -0.01])
    linear_extrude(height = thickness + 0.02)
        offset(r = offset)
            import(source, center = false);

    // Registration pin holes at board corners
    pin_holes();
}
