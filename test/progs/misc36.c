/* misc36.c - RESPIN 36: the cycle counter (lisa_cyccnt.v) and the PDM
 * outputs (Timer 3's channels in PDM mode, lisa_timer3.v IE [6:5]).  The
 * GF180 chip has no watchdog (GF180.md): its registers 0x4C-0x4F read 0,
 * and the sky130 version's checks 3 / 4 (kicks, the reset, WDRST) are not
 * here.
 *
 *  1 the cycle counter counts: a loop of known length, CYC0 latching 31:8
 *  2 a write clears it
 *  3 the watchdog's registers read 0 and take no writes
 *  5 Timer 3's channels in PDM mode at 64 and 192 (CMP0 / CMP1's low
 *    bytes; 25% and 75%: test.py measures them on uo[1] / uo[2], mux 2) -
 *    left running
 */
#include "harness.h"

__sfr __at(0x248) CYC0;
__sfr __at(0x249) CYC1;
__sfr __at(0x24A) CYC2;
__sfr __at(0x24B) CYC3;
__sfr __at(0x24C) WDT_CTRL;
__sfr __at(0x24D) WDT_KICK;
__sfr __at(0x24E) WDT_TIMEOUT;
__sfr __at(0x24F) WDT_STAT;
__sfr __at(0x235) T3_CMP0_L;
__sfr __at(0x237) T3_CMP1_L;
__sfr __at(0x23D) T3_CTRL;
__sfr __at(0x23E) T3_IE;

static unsigned long cycles(void)
{
  unsigned long v = CYC0;              /* latches 31:8 */
  v |= (unsigned long)CYC1 << 8;
  v |= (unsigned long)CYC2 << 16;
  v |= (unsigned long)CYC3 << 24;
  return v;
}

static void wait_cycles(unsigned long n)
{
  unsigned long t = cycles();
  while (cycles() - t < n)
    ;
}

void main(void)
{
  unsigned long a, b;
  unsigned char i;

  puts("misc36\n");
  a = cycles();
  for (i = 0; i < 100; i++)
    ;
  b = cycles();
  CHECK(1, b > a && b - a > 200 && b - a < 200000);

  CYC0 = 0;
  a = cycles();
  CHECK(2, a < 1000);

  WDT_TIMEOUT = 1;                     /* no watchdog: nothing takes */
  WDT_CTRL = 1;
  wait_cycles(1000);
  CHECK(3, WDT_CTRL == 0 && WDT_TIMEOUT == 0 && WDT_KICK == 0 && WDT_STAT == 0);

  T3_CMP0_L = 64;                      /* the PDM levels */
  T3_CMP1_L = 192;
  T3_IE = 0x60;                        /* PDM0, PDM1: no captures, no interrupts */
  T3_CTRL = 0x06;                      /* PWM0 / PWM1 out (uo[1] / uo[2]) */
  CHECK(5, T3_IE == 0x60 && T3_CMP0_L == 64 && T3_CMP1_L == 192);
  DONE();
  for (;;)
    ;
}
