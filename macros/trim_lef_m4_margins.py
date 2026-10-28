#!/usr/bin/env python3
"""Drop the RAM32 LEF's Metal4 obstructions in the macro's top and bottom
margins (GF180.md, 2026-10-28).

Magic's abstract blankets every layer that has geometry, so the LEF carries
full-width Metal4 OBS strips over the die margins (y 0.09-3.32 and
165.24-168.47 of the 168.56 um die) although, since the DFFRAM flow routes
the GF180 RAM32 with ROUTING_OBSTRUCTIONS on Metal4 there, nothing is drawn
on Metal4 in those strips: only the power pins (y 3.62-164.94) and the
signal routing between the rows.  The Tiny Tapeout tile's power stripes run
through the margins to reach the macro's pins (odb_stripes.py), and with
the strips in the LEF Magic's extraction reports every crossing as an
"Illegal overlap between obsm4 and metal4" (132 in gf15).

usage: trim_lef_m4_margins.py RAM32.lef [ymin ymax]   (defaults 3.62 164.94)
Rewrites the file in place; prints what it removed."""
import re, sys

path = sys.argv[1]
ymin = float(sys.argv[2]) if len(sys.argv) > 2 else 3.62
ymax = float(sys.argv[3]) if len(sys.argv) > 3 else 164.94
text = open(path).read()
head, obs, tail = re.match(r"(.*?\n\s*OBS\n)(.*?)(\n\s*END\n.*)", text, re.S).groups()
out, layer, removed, kept = [], None, [], 0
for line in obs.split("\n"):
    m = re.match(r"\s*LAYER (\S+)", line)
    if m:
        layer = m.group(1)
    r = re.match(r"(\s*RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;)", line)
    if r and layer == "Metal4":
        x1, y1, x2, y2 = (float(v) for v in r.groups()[1:5])
        if y2 <= ymin + 0.01 or y1 >= ymax - 0.01:
            removed.append((x1, y1, x2, y2))
            continue
        kept += 1
    out.append(line)
open(path, "w").write(head + "\n".join(out) + tail)
print(f"{path}: removed {len(removed)} Metal4 OBS rect(s) in the margins, kept {kept}:")
for r in removed:
    print("   RECT %.2f %.2f %.2f %.2f" % r)
