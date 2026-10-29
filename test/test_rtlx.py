# RTL: which signals under the chip are X while the core runs?  Those are the
# candidates for the gate-level divergence (RTL if/case resolve an X select
# to the else branch; the gates propagate it).
import cocotb
from cocotb.triggers import ClockCycles
from cocotb.handle import HierarchyObject, HierarchyArrayObject
from lisa import REG_STATUS, REG_PC
from test import start

sigs = []


def collect(h, depth=0):
    for sub in h:
        try:
            if isinstance(sub, (HierarchyObject, HierarchyArrayObject)):
                if depth < 6:
                    collect(sub, depth + 1)
            else:
                sigs.append(sub)
        except Exception:
            pass


def x_list(skip_mem=True):
    out = []
    for s in sigs:
        try:
            if len(s) > 64 and skip_mem:
                continue
            v = str(s.value)
        except Exception:
            continue
        if 'x' in v.lower() or 'z' in v.lower():
            out.append(s._path.replace('tb.lisa.', ''))
    return out


@cocotb.test()
async def rtl_x(dut):
    lisa = await start(dut)
    collect(dut.lisa)
    dut._log.info('%d signals under the chip' % len(sigs))
    await lisa.setup(cache=False, quad=True)
    await lisa.core_reset()
    await lisa.write_reg(REG_PC, 0)
    dut._log.info('halted: PC %04x STATUS %04x' % (await lisa.read_reg(REG_PC), await lisa.read_reg(REG_STATUS)))
    xs = x_list()
    dut._log.info('halted: %d X signals: %s' % (len(xs), ' '.join(xs)))
    await lisa.resume()
    t = 0
    for step in [4000, 1000, 1000, 1000, 1000, 4000, 4000, 16000]:
        await ClockCycles(dut.clk, step)
        t += step
        xs = x_list()
        dut._log.info('resume +%d: PC %04x, %d X signals: %s' % (t, int(dut.lisa.i_lisa_core.pc.value), len(xs), ' '.join(xs)))
