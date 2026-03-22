SCAD     = gen_stl.scad
OPENSCAD = openscad

# Example:
#   make run SOURCE=sample/4servoboard-F_Paste.dxf TARGET=out.stl \
#            WIDTH=80 HEIGHT=60 THICKNESS=0.16 OFFSET=0.1

run:
	$(OPENSCAD) \
	  -D 'source="$(SOURCE)"' \
	  -D 'width=$(WIDTH)' \
	  -D 'height=$(HEIGHT)' \
	  -D 'thickness=$(THICKNESS)' \
	  -D 'offset=$(OFFSET)' \
	  -o "$(TARGET)" $(SCAD)
