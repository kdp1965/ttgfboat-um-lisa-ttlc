# Gate level: does the RAM path (data cache + RAM32 macro) work at all?  The
# debugger writes bytes while the core is halted and reads them back; last,
# it reads a byte never written (X in the macro's latches) to see whether an
# X on the data path takes the debug controller down with it.
import cocotb
from cocotb.triggers import ClockCycles
from lisa import REG_STATUS, REG_PC, Timeout
from test import start
from test_glprobe import gl_x_nets, fmt_x

@cocotb.test()
async def gl_ram(dut):
    lisa = await start(dut)
    await lisa.setup(cache=True, quad=True)     # the data cache on: 0x100 and 0x000 are different bytes
    await lisa.core_reset()
    await lisa.write_reg(REG_PC, 0)
    dut._log.info('halted: STATUS %04x' % await lisa.read_reg(REG_STATUS))
    pat = {0x0000: 0x5a, 0x0001: 0xa5, 0x0002: 0x01, 0x0003: 0xfe, 0x0010: 0x33, 0x0040: 0x77, 0x0100: 0x88, 0x7ffe: 0x99, 0x7fff: 0x12}
    for a, v in pat.items():
        await lisa.write_ram(a, v)
    bad = 0
    for a, v in pat.items():
        try:
            got = await lisa.read_ram(a)
        except Timeout:
            dut._log.info('  RAM[%04x]: NO REPLY' % a); bad += 1; continue
        if got != v:
            bad += 1
        dut._log.info('  RAM[%04x] wrote %02x read %02x%s' % (a, v, got, '' if got == v else '  MISMATCH'))
    dut._log.info('%d mismatches; X nets %s' % (bad, fmt_x(gl_x_nets(dut))))
    dut._log.info('reading a byte never written (0x0020)...')
    try:
        got = await lisa.read_ram(0x0020)
        dut._log.info('  RAM[0020] read %02x' % got)
    except Exception as e:
        dut._log.info('  RAM[0020]: %s' % e)
    dut._log.info('after: X nets %s' % fmt_x(gl_x_nets(dut)))
    try:
        dut._log.info('STATUS now %04x' % await lisa.read_reg(REG_STATUS))
    except Timeout:
        dut._log.info('STATUS: NO REPLY - the debugger is gone')
