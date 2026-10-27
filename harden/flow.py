#!/usr/bin/env python3
"""flow.py [--macro] [run-tag] - harden tt_um_pettit_lisa locally with LibreLane's
Classic flow on gf180mcuD, on config_merged.json (configure.py;
config_merged_macro.json with --macro).  With --macro the RAM32 DFFRAM macro
is in the design and one extra step runs the tile's vertical power stripes
across its pin columns after the PDN is generated (the single-layer tile PDN
does not reach a macro's pins by itself; odb_stripes.py).

    python3 flow.py [--macro] [--to=Step.Id] [--from=Step.Id] [tag]
        inside the LibreLane nix shell, PDK_ROOT set
        (--to=Yosys.Synthesis: synthesis only, `make synth`)

The sky130 flow this came from (ttsky26d-um-lisa-ttlc harden/flow.py) also
anchored the registers to a reference placement and drew Calvin as placement
blockages; neither is carried over to GF180.
"""
import json
import os
import sys

from librelane.flows.classic import Classic
from librelane.steps import OpenROAD
from librelane.steps.odb import OdbpyStep

HERE = os.path.dirname(os.path.abspath(__file__))
PDK = "gf180mcuD"
PDN_VERTICAL_LAYER = "Metal4"


class ExtendPowerStripes(OdbpyStep):
    id = "Tile.ExtendPowerStripes"
    name = "Extend Power Stripes Over Macros"

    def get_script_path(self):
        return os.path.join(HERE, "odb_stripes.py")

    def get_command(self):
        # the tile's vertical PDN layer: Metal4 on gf180mcuD (odb_stripes.py's
        # default is sky130's met4; the PDK's PDN_VERTICAL_LAYER is not in
        # this step's configuration view)
        return super().get_command() + ["--layer", PDN_VERTICAL_LAYER]


class StandardFlow(Classic):
    Steps = list(Classic.Steps)


class MacroFlow(Classic):
    Steps = list(Classic.Steps)
    Steps.insert(Steps.index(OpenROAD.GeneratePDN) + 1, ExtendPowerStripes)


def main():
    macro = "--macro" in sys.argv
    to = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--to=")), None)
    frm = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--from=")), None)   # resume an existing run (its tag) from this step
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    merged = "config_merged_macro.json" if macro else "config_merged.json"
    cfg = json.load(open(os.path.join(HERE, merged), encoding="utf8"))
    cfg["PDK"] = PDK
    flow_class = MacroFlow if macro else StandardFlow
    flow = flow_class(cfg, design_dir=HERE, pdk_root=os.environ["PDK_ROOT"])
    flow.start(tag=args[0] if args else None, **({"to": to} if to else {}), **({"frm": frm} if frm else {}))


if __name__ == "__main__":
    main()
