# Test programs for the revision-3 RTL (sdcc -mlisa --rev3 from lisa-tools:
# the third chip's 24-bit registers and three-byte pairs, REV3.md; the
# default stack at 0x7f, inside the 128-byte RAM the cache-off tests use;
# the .hex images are committed so the testbenches run without the compiler).
# A --rev2 image does not run on this core (its pairs are two bytes).
#   make            build *.ihx and the *.hex the flash model / tb_core load
SDCC      ?= ../../../lisa-tools/sdcc-lisa/build/bin/sdcc
SDCC_TEST ?= ../../../lisa-tools/sdcc_test
CFLAGS    ?= -mlisa --rev3 --debug -I$(SDCC_TEST)

PROGS = hello alu2 reti div16 cache14 dbg swap bank uartov spi timer3 ws2812 wsdma i2c misc36

all: $(PROGS:%=%.hex) bank_test.hex spi_test.hex

# (the sky130 chip's TTLC programs, ttlc/, are not here: no TTLC on the GF180 chip)

# spi_test.hex: the committed image carries the sky130 chip's TTLC loopback at
# 0x10000 behind spi.hex (unused here); rebuilt it is spi.hex alone
spi_test.hex: spi.hex
	cp $< $@


%.ihx: %.c $(SDCC_TEST)/harness.h
	$(SDCC) $(CFLAGS) -o $@ $<

# the cache test uses the 32K data space: stack at the top, data low (TT07's
# --tt07-cache laid that out with its workarounds; --rev2 excludes it)
cache14.ihx: CFLAGS += --stack-loc 0x7fff
bank.ihx: CFLAGS += --stack-loc 0x7fff
wsdma.ihx: CFLAGS += --stack-loc 0x7fff
i2c.ihx: CFLAGS += --stack-loc 0x7fff

# the bank test (RESPIN 22): bank.c at 0 and `ldi #bank; ret` at word 0x4000
# of code banks 1, 2, 3 (flash bytes 0x8000, 0x10000, 0x18000: bank_stubs.hex)
bank_test.hex: bank.hex bank_stubs.hex ../hexcat.py
	python3 ../hexcat.py $@ 0 bank.hex 0 bank_stubs.hex

%.hex: %.ihx ../ihx2hex.py
	python3 ../ihx2hex.py $< $@

clean:
	rm -f *.ihx *.hex *.asm *.lst *.rst *.rel *.sym *.map *.lk *.cdb *.adb *.mem *.noi

.PHONY: all clean
.PRECIOUS: %.ihx
