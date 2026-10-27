#!/usr/bin/env python3
"""configure.py [--macro] [--tiles=3x4] - the LibreLane configuration for a
local harden on gf180mcuD, built the way tt-support-tools' --create-user-config
--gf does it: the sources, die area and floorplan template from ../info.yaml's
tile, merged over ../src/config.json; with --macro, macro.json on top (the
RAM32 DFFRAM macro in place of src/RAM32.v).  --tiles=WxH tries another tile
(its tt_block_WxH_pgvdd.def must be here); with --macro, macro_WxH.json is then
merged last: its MACRO_LOCATIONS {instance: [x, y]} move the macros, the
rest are plain variables.  --overlay=FILE merges one more JSON of plain
variables last (a per-run trial: `make macro OVERLAY=trial.json`).  Writes
config_merged.json, or
config_merged_macro.json with --macro, so the two flows can run at the same
time."""
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TILE_SIZES = {                       # tt-support-tools tech/gf180mcuD/tile_sizes.yaml (ttgf26c; a copy is here)
    "1x1": [0, 0, 346.64, 160.72], "1x2": [0, 0, 346.64, 325.36],
    "2x2": [0, 0, 711.20, 325.36], "3x2": [0, 0, 1075.76, 325.36],
    "3x4": [0, 0, 1075.76, 736.96], "4x2": [0, 0, 1440.32, 325.36],
    "4x4": [0, 0, 1440.32, 736.96],
    # 5x4: one more tile column (364.56 um per column: 346.64, 711.20, 1075.76,
    # 1440.32); not in tt-support-tools' table (2026-10-27) - tt_block_5x4_pgvdd.def
    # here is the 4x4 template with that die (the pins sit at the left of the
    # top edge in every template, as in TT's own sky130 5x4), and the
    # submission needs Tiny Tapeout to add the size, as they did for the
    # sky130 chip's 5x4
    "5x4": [0, 0, 1804.88, 736.96],
}
DEF_TEMPLATE = "tt_block_%s_pgvdd.def"      # tt-support-tools tech/gf180mcuD/def/
SCL_LIB = "pdk_dir::libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__%s.lib"


def load_json(path):
    with open(path, encoding="utf8") as f:
        return json.load(f)


def main():
    macro = "--macro" in sys.argv
    info = yaml.safe_load(open(os.path.join(ROOT, "info.yaml")))["project"]
    tiles = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--tiles=")), info["tiles"])
    sources = list(info["source_files"])
    cfg = load_json(os.path.join(ROOT, "src", "config.json"))
    # src/config.json's dir:: paths are relative to src/; config_merged.json lives here
    for k, v in cfg.items():
        if isinstance(v, str) and v.startswith("dir::"):
            cfg[k] = "dir::../src/" + v[5:]
    if macro:
        over = load_json(os.path.join(HERE, "macro.json"))
        for s in over.pop("REMOVE_SOURCES", []):
            sources.remove(s)
        cfg.update(over)
        tile_json = os.path.join(HERE, "macro_%s.json" % tiles)
        if os.path.exists(tile_json):
            tile_over = load_json(tile_json)
            for inst, loc in tile_over.pop("MACRO_LOCATIONS", {}).items():
                for m in cfg["MACROS"].values():
                    if inst in m["instances"]:
                        m["instances"][inst]["location"] = loc
            cfg.update(tile_over)
    cfg["DRT_SAVE_DRC_REPORT_ITERS"] = 4        # a DRC report every 4 router iterations (status.py)
    cfg.update({
        "DESIGN_NAME": info["top_module"],
        "VERILOG_FILES": ["dir::../src/" + s for s in sources],
        "DIE_AREA": TILE_SIZES[tiles],
        "FP_DEF_TEMPLATE": "dir::" + DEF_TEMPLATE % tiles,
        "VDD_PIN": "VPWR",                     # LibreLane's gf180mcuD names (the cells' VDD / VSS are connected to them)
        "GND_PIN": "VGND",
        "RT_MAX_LAYER": "Metal4",
        # The 3.3 V corners (tt_tool.py --create-user-config --gf writes these:
        # LibreLane's gf180mcuD defaults are the 5 V ones; it also writes
        # LIB_SYNTH / LIB_FASTEST / LIB_SLOWEST, which this LibreLane's
        # Python API rejects as unknown keys, so they are left out)
        "VDD_PIN_VOLTAGE": 3.3,
        "DEFAULT_CORNER": "nom_tt_025C_3v30",
        "STA_CORNERS": ["%s_%s" % (rc, c) for rc in ("nom", "min", "max") for c in ("tt_025C_3v30", "ss_125C_3v00", "ff_n40C_3v60")],
        "LIB": {"*_%s" % c: [SCL_LIB % c] for c in ("tt_025C_3v30", "ss_125C_3v00", "ff_n40C_3v60")},
    })
    if not os.path.exists(os.path.join(HERE, DEF_TEMPLATE % tiles)):
        sys.exit("harden/%s is missing: fetch it from tt-support-tools (branch ttgf26c) tech/gf180mcuD/def" % (DEF_TEMPLATE % tiles))
    # the overlay last: a trial may override anything, the die and the
    # template included (a timing trial on a die the design fits, say)
    overlay = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--overlay=")), None)
    if overlay:
        cfg.update({k: v for k, v in load_json(overlay).items() if k != "//"})
    # the template writes its booleans as 0 / 1, which LibreLane's Python API
    # refuses to convert
    BOOL_PREFIXES = ("RUN_", "ERROR_ON_", "LINTER_INCLUDE", "DESIGN_REPAIR_", "MAGIC_DEF", "MAGIC_WRITE")
    BOOL_KEYS = ("GRT_ALLOW_CONGESTION", "FP_PDN_MULTILAYER", "PDN_MULTILAYER", "FP_PDN_CHECK_NODES")
    for k, v in list(cfg.items()):
        if type(v) is int and v in (0, 1) and (k.startswith(BOOL_PREFIXES) or k in BOOL_KEYS):
            cfg[k] = bool(v)
    cfg = {k: v for k, v in cfg.items() if k != "//"}
    out = os.path.join(HERE, "config_merged_macro.json" if macro else "config_merged.json")
    with open(out, "w", encoding="utf8") as f:
        json.dump(cfg, f, indent=2)
    print("%s: %s tile %s, %d sources%s%s" % (out, info["top_module"], tiles, len(sources),
                                               ", the RAM32 macro" if macro else "",
                                               ", overlay %s" % overlay if overlay else ""))
    if tiles != info["tiles"]:
        print("   (info.yaml says %s: this is a trial on another tile)" % info["tiles"])


if __name__ == "__main__":
    main()
