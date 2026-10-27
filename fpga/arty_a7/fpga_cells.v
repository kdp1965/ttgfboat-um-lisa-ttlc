// The GF180 cells (gf180mcu_fd_sc_mcu7t5v0) debug_regs.v and lisa_dbg.v
// instantiate, for the FPGA.
//
// The chip keeps its static debug registers (base addresses, the output
// and I/O muxes, breakpoints) in latrnq latches gated by the debug write
// strobe.  On the FPGA they are flops: latch2flop.py rewrites the two
// files so that each latch is an fpga_dlrtp clocked by the module's clk,
// which captures D at the clock edges while E is high - the strobe is
// a whole-cycle signal with dbg_di stable, so the value is the one the
// latch would hold.
module fpga_dlrtp
(
   input  wire    CLK,
   input  wire    RN,
   input  wire    E,
   input  wire    D,
   output reg     Q
);
   always @(posedge CLK or negedge RN)
   begin
      if (!RN)
         Q <= 1'b0;
      else if (E)
         Q <= D;
   end
endmodule

module gf180mcu_fd_sc_mcu7t5v0__and2_4
(
   input  wire    A1,
   input  wire    A2,
   output wire    Z
);
   assign Z = A1 & A2;
endmodule
