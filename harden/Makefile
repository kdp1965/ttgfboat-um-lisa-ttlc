# Harden tt_um_pettit_lisa on gf180mcuD on this machine with LibreLane (the
# GitHub runners take an hour for what the Mac does in minutes).
#
#   make            # the standard Tiny Tapeout flow: the RAM synthesized from src/RAM32.v
#   make macro      # with the RAM32 DFFRAM macro (macro.json, the stripe step of flow.py)
#   make synth      # synthesis only (runs/synth-<tag>/*-yosys-synthesis/reports): area, cell types
#   make clean
#
# LibreLane and the tools come from the dev shell of a LibreLane checkout
# (LIBRELANE), the PDK from PDK_ROOT (ciel enable --pdk-family gf180mcu <the
# open_pdks commit librelane/open_pdks_rev names>).  Run outside the shell,
# each recipe re-runs itself inside it.  Results: runs/<tag>/final/.
LIBRELANE ?= $(HOME)/projects/tiny_tapeout/librelane
# The PDK version is the one tt-support-tools (branch ttgf26c) enables for the
# GF180 shuttle's action (gf180mcuD, open_pdks 54435919): the ciel symlink in
# ~/projects/fossi may point at a newer one whose LibreLane configuration this
# LibreLane reads with an empty LIB, so the version directory is named here.
# (set unconditionally: a PDK_ROOT in the environment, ~/projects/fossi
# usually, would otherwise win; make PDK_ROOT=... still overrides)
GF180_PDK_VERSION ?= 54435919abffb937387ec956209f9cf5fd2dfbee
export PDK_ROOT = $(HOME)/projects/fossi/ciel/gf180mcu/versions/$(GF180_PDK_VERSION)
TAG ?= $(shell date +%Y%m%d-%H%M%S)
# TO=Step.Id stops after that step: TO=OpenROAD.GlobalRouting shows the
# congestion report before the hours of detailed routing.
TO ?=
FLOW_TO = $(if $(TO),--to=$(TO),)
# TILES=3x4 tries another tile (harden/tt_block_3x4_pgvdd.def, macro_3x4.json)
TILES ?=
CONF_TILES = $(if $(TILES),--tiles=$(TILES),)
# OVERLAY=trial.json: a JSON of variables merged last (a per-run trial)
OVERLAY ?=
CONF_TILES += $(if $(OVERLAY),--overlay=$(OVERLAY),)

ifeq ($(IN_NIX_SHELL),)
NIX_RUN = nix-shell $(LIBRELANE)/shell.nix --run
else
NIX_RUN = sh -c
endif

standard:
	$(NIX_RUN) "python3 configure.py $(CONF_TILES) && python3 flow.py $(FLOW_TO) standard-$(TAG)"

macro:
	$(NIX_RUN) "python3 configure.py --macro $(CONF_TILES) && python3 flow.py --macro $(FLOW_TO) macro-$(TAG)"

synth:
	$(NIX_RUN) "python3 configure.py $(CONF_TILES) && python3 flow.py --to=Yosys.Synthesis synth-$(TAG)"

# Where is the run (the newest under runs/, or RUN=runs/<tag>): the steps
# done and their durations, the current step's log tail, and once the
# detailed router runs its iterations and the newest DRC report (by layer,
# type, densest bins, nets).  harden-stop kills a router that will not
# converge; the flow fails there and the report on disk is the one to read.
RUN ?=
status:
	python3 status.py $(RUN)

harden-stop:
	python3 status.py $(RUN) --stop

shell:
	nix-shell $(LIBRELANE)/shell.nix

clean:
	rm -rf runs config_merged.json config_merged_macro.json

.PHONY: standard macro synth status harden-stop shell clean
