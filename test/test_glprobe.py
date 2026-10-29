# A probe for the gate-level build: the debugger reads the flash through the
# chip's QSPI and the core sits halted, but once released the debugger stops
# answering (the program tests time out with no output).  Which part dies?
# The gate-level run scans every named net of the netlist for X; the RTL run (GATES=no) samples
# the same few control signals for comparison.
#   make SIM=icarus GATES=yes MACRO_NETLIST=../macros/RAM32.pnl.v CACHE=1 MODULE=test_glprobe COCOTB_TEST_MODULES=test_glprobe
import os
import re
import cocotb
from cocotb.triggers import ClockCycles
from lisa import REG_STATUS, REG_PC, REG_DBG_ADDR_L, REG_DBG_ADDR_H, REG_LISA1_BASE, Timeout
from test import start

GL = os.environ.get('GATES', 'no') == 'yes'
SMALL = [('i_inst_stream', 'state'), ('i_inst_stream', 'count'), ('i_inst_stream', 'qspi_valid'),
         ('i_inst_stream', 'pushed'), ('i_inst_stream', 'have_pos'), ('i_inst_stream', 'abort_req'),
         ('i_lisa_core', 'inst'), ('i_lisa_core', 'cond'), ('i_lisa_core', 'pc'), ('i_lisa_core', 'sp')]

handles = {}


def gl_handles(dut):
    if handles:
        return handles
    # the named nets of the flat netlist (`wire \\inst.sig[bit] ;` lines)
    names = re.findall(r'^\s*wire \\(\S+) ;', open(os.path.join(os.path.dirname(__file__), 'gate_level_netlist.v')).read(), re.M)
    for n in names:
        try:
            handles[n] = dut.lisa._id('\\' + n, extended=False)
        except Exception:
            pass
    return handles


def gl_x_nets(dut):
    """the vectors with an X bit, as name -> bit list"""
    xs = {}
    for n, h in gl_handles(dut).items():
        if 'x' in str(h.value).lower() or 'z' in str(h.value).lower():
            m = re.match(r'(.*)\[(\d+)\]$', n)
            if m:
                xs.setdefault(m.group(1), []).append(int(m.group(2)))
            else:
                xs.setdefault(n, []).append(-1)
    return xs


def fmt_x(xs):
    out = []
    for n in sorted(xs):
        bits = sorted(xs[n])
        out.append(n if bits == [-1] else '%s[%d..%d]%s' % (n, bits[0], bits[-1], '' if len(bits) == bits[-1] - bits[0] + 1 else '(%d)' % len(bits)))
    return '%d: ' % len(xs) + ' '.join(out)


def small(dut):
    out = []
    for inst, sig in SMALL:
        try:
            if GL:
                bits = {}
                for n, h in gl_handles(dut).items():
                    m = re.match(r'%s\.%s(\[(\d+)\])?$' % (re.escape(inst), re.escape(sig)), n)
                    if m:
                        bits[int(m.group(2) or 0)] = str(h.value)
                v = ''.join(bits[i] for i in sorted(bits, reverse=True)) if bits else '?'
            else:
                v = str(getattr(getattr(dut.lisa, inst), sig).value)
            out.append('%s.%s=%s' % (inst, sig, v))
        except Exception:
            out.append('%s.%s=?' % (inst, sig))
    return ' '.join(out)


async def try_read(lisa, dut, a, what):
    try:
        v = await lisa.read_reg(a)
        dut._log.info('  read %s (0x%02x) = %04x' % (what, a, v))
    except Timeout:
        dut._log.info('  read %s (0x%02x): NO REPLY' % (what, a))


@cocotb.test()
async def gl_probe(dut):
    lisa = await start(dut)
    await lisa.setup(cache=False, quad=True)
    await lisa.write_reg(REG_DBG_ADDR_H, 0)
    await lisa.write_reg(REG_DBG_ADDR_L, 0)
    words = [await lisa.read_reg(0x20) for _ in range(4)]
    dut._log.info('flash words through the debug QSPI: %s' % ' '.join('%04x' % w for w in words))
    await lisa.core_reset()
    await lisa.write_reg(REG_PC, 0)
    dut._log.info('halted: PC %04x STATUS %04x' % (await lisa.read_reg(REG_PC), await lisa.read_reg(REG_STATUS)))
    dut._log.info('halted: ' + small(dut))
    if GL:
        dut._log.info('halted X nets %s' % fmt_x(gl_x_nets(dut)))
    await lisa.resume()
    t = 0
    for step in [2000, 2000, 2000, 2000, 2000, 2000, 4000, 8000, 8000, 16000, 16000, 16000]:
        await ClockCycles(dut.clk, step)
        t += step
        line = 'resume +%d: uo_out %s %s' % (t, str(dut.uo_out.value), small(dut))
        if GL:
            line += ' | X nets ' + fmt_x(gl_x_nets(dut))
        dut._log.info(line)
    await try_read(lisa, dut, REG_LISA1_BASE, 'LISA1_BASE (debug_regs latch)')
    if GL:
        dut._log.info('after the read: X nets ' + fmt_x(gl_x_nets(dut)))
    await try_read(lisa, dut, REG_STATUS, 'STATUS (core register)')
