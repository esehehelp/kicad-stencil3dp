"""Install the stencil3dp plugin into KiCad's scripting/plugins directory."""

import os
import shutil
import sys

# KiCad 9.x default plugin directory on Windows
KICAD_PLUGIN_DIR = os.path.join(
    os.path.expanduser("~"),
    "Documents", "KiCad", "9.0", "scripting", "plugins"
)

SRC_DIR  = os.path.join(os.path.dirname(__file__), "stencil3dp")
DEST_DIR = os.path.join(KICAD_PLUGIN_DIR, "stencil3dp")


def install():
    if not os.path.isdir(SRC_DIR):
        print(f"ERROR: source directory not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(DEST_DIR):
        print(f"Removing existing installation: {DEST_DIR}")
        shutil.rmtree(DEST_DIR)

    print(f"Copying {SRC_DIR} -> {DEST_DIR}")
    shutil.copytree(SRC_DIR, DEST_DIR)

    # Also copy gen_stl.scad next to the plugin package so the relative path works
    scad_src  = os.path.join(os.path.dirname(__file__), "gen_stl.scad")
    scad_dest = os.path.join(KICAD_PLUGIN_DIR, "gen_stl.scad")
    if os.path.isfile(scad_src):
        print(f"Copying gen_stl.scad -> {scad_dest}")
        shutil.copy2(scad_src, scad_dest)

    print("\nInstallation complete.")
    print("Restart KiCad, then use Tools -> External Plugins -> Stencil 3DP.")


if __name__ == "__main__":
    install()
