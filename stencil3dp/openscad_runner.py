"""Subprocess wrapper for OpenSCAD CLI."""

import subprocess
import shutil


def _find_openscad():
    """Try to locate the openscad executable."""
    # Check PATH first
    found = shutil.which("openscad")
    if found:
        return found
    # Common Windows install location
    import os
    candidates = [
        r"C:\Program Files\OpenSCAD\openscad.exe",
        r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "openscad"  # fall back and let subprocess raise


class OpenScadRunner:
    def __init__(self, openscad_path=None):
        self.openscad_path = openscad_path or _find_openscad()

    def render(self, scad_path, dxf_path, stl_path,
               width, height, thickness, offset, pin_dia=1.5, pin_margin=3.0):
        """Run OpenSCAD to generate an STL from a SCAD + DXF pair.

        Raises:
            FileNotFoundError: if openscad executable not found.
            subprocess.CalledProcessError: if openscad exits with error.
        """
        cmd = [
            self.openscad_path,
            "-D", f'source="{dxf_path}"',
            "-D", f"width={width}",
            "-D", f"height={height}",
            "-D", f"thickness={thickness}",
            "-D", f"offset={offset}",
            "-D", f"pin_dia={pin_dia}",
            "-D", f"pin_margin={pin_margin}",
            "-o", stl_path,
            scad_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )
        return stl_path
