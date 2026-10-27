// Behavioural models of the two GF180 cells debug_regs.v and lisa_dbg.v
// instantiate (gf180mcu_fd_sc_mcu7t5v0), for the RTL simulation.
module gf180mcu_fd_sc_mcu7t5v0__and2_4
(
   input  wire A1,
   input  wire A2,
   output wire Z
);

   assign Z = A1 & A2;

endmodule

module gf180mcu_fd_sc_mcu7t5v0__latrnq_1
(
   input  wire RN,
   input  wire E,
   input  wire D,
   output reg  Q
);

   always @*
   begin
      if (~RN)
         Q = 1'b0;
      else if (E)
         Q = D;
   end

endmodule
