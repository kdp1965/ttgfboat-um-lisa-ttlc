# A clock-by-clock trace of the core <-> cache <-> RAM32 interface around the
# first X of the gate-level run (resume +5600 .. +6200), on the RTL and the
# gates alike, to diff.  Lines where the RAM is accessed or d_i / acc change.
import os
import re
import cocotb
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly
from lisa import REG_STATUS, REG_PC
from test import start

GL = os.environ.get('GATES', 'no') == 'yes'


class Vec:
    def __init__(self, dut, name, width):
        self.bits = []
        if GL:
            for i in range(width):
                try:
                    self.bits.append(dut.lisa._id('\\%s[%d]' % (name, i), extended=False))
                except Exception:
                    self.bits.append(None)
        else:
            self.h = dut.lisa
            for p in name.split('.'):
                self.h = getattr(self.h, p)

    def __str__(self):
        if GL:
            return ''.join('?' if b is None else str(b.value) for b in reversed(self.bits))
        return str(self.h.value)


def hx(s):
    s = s.replace('?', 'x')
    if 'x' in s.lower() or 'z' in s.lower():
        # hex with X nibbles
        out = ''
        s = s.zfill((len(s) + 3) // 4 * 4)
        for i in range(0, len(s), 4):
            n = s[i:i + 4]
            out += 'X' if ('x' in n.lower() or 'z' in n.lower()) else '%x' % int(n, 2)
        return out
    return '%0*x' % ((len(s) + 3) // 4, int(s, 2))


@cocotb.test()
async def gl_trace(dut):
    lisa = await start(dut)
    await lisa.setup(cache=False, quad=True)
    await lisa.core_reset()
    await lisa.write_reg(REG_PC, 0)
    sig = {
        'pc': Vec(dut, 'i_lisa_core.pc', 15), 'd_addr': Vec(dut, 'd_addr', 23), 'd_o': Vec(dut, 'd_o', 8),
        'd_i': Vec(dut, 'i_lisa_core.d_i', 8), 'acc': Vec(dut, 'i_lisa_core.acc' if not GL else 'acc', 8),
        'cstate': Vec(dut, 'i_data_cache.state', 10 if GL else 4),
    }
    ram = dut.lisa.ram1
    await lisa.resume()
    await ClockCycles(dut.clk, 5600)
    last = None
    for t in range(5600, 6200):
        await RisingEdge(dut.clk)
        await ReadOnly()
        en, we = str(ram.EN0.value), str(ram.WE0.value)
        line = 'pc %s da %s do %s di %s acc %s cs %s | ram EN %s WE %s A %s Di %s Do %s' % (
            hx(str(sig['pc'])), hx(str(sig['d_addr'])), hx(str(sig['d_o'])), hx(str(sig['d_i'])), hx(str(sig['acc'])),
            str(sig['cstate']), en, we, hx(str(ram.A0.value)), hx(str(ram.Do0.value if False else ram.Di0.value)), hx(str(ram.Do0.value)))
        if en == '1' or we not in ('0000',) or last is None or line.split('|')[0] != last.split('|')[0]:
            dut._log.info('+%d %s' % (t, line))
        last = line
