// The RAM32 macro's gate-level netlist on its own (make macro-gl): byte and
// word writes in the chip's pattern (WE for one clock, A / Di from flops,
// so set right after the rising edge) read back.  Words 1-3 of every 8
// (0x03, 0x11, 0x1b here) had an undriven select until the DEC3x8 fix in
// DFFRAM.librelane's gf180 platform (GF180.md): they read X.
`timescale 1ns / 1ps
module tb_ram32;
   reg clk = 0; always #22.5 clk = ~clk;
   reg en = 1; reg [3:0] we = 0; reg [4:0] a = 0; reg [31:0] di = 0; wire [31:0] dout;
   supply1 vpwr; supply0 vgnd;
   integer fails = 0;
   RAM32 ram (.CLK(clk), .EN0(en), .VPWR(vpwr), .VGND(vgnd), .A0(a), .Di0(di), .Do0(dout), .WE0(we));
   // a write as the cache does it: A / WE / Di change just after the rising edge, WE for one clock
   task wr(input [4:0] ad, input [3:0] w, input [31:0] d); begin
      @(posedge clk); #1; a = ad; we = w; di = d; @(posedge clk); #1; we = 0; di = 32'hxxxxxxxx; end endtask
   task rd(input [4:0] ad, input [31:0] exp, input [31:0] mask); begin
      @(posedge clk); #1; a = ad; @(posedge clk); @(posedge clk); #1;
      if ((dout & mask) === (exp & mask)) $display("  ok    %02x -> %h", ad, dout);
      else begin $display("  FAIL  %02x -> %h (want %h on %h)", ad, dout, exp, mask); fails = fails + 1; end end endtask
   initial begin
      #200;
      wr(5'h03, 4'b1111, 32'hdeadbeef); rd(5'h03, 32'hdeadbeef, 32'hffffffff);
      wr(5'h11, 4'b1111, 32'hcafef00d); rd(5'h11, 32'hcafef00d, 32'hffffffff);
      wr(5'h1b, 4'b1111, 32'h01234567); rd(5'h1b, 32'h01234567, 32'hffffffff);
      wr(5'h00, 4'b0001, 32'h5a5a5a5a); rd(5'h00, 32'h0000005a, 32'h000000ff);
      wr(5'h1f, 4'b0100, 32'h00000000); rd(5'h1f, 32'h00000000, 32'h00ff0000);
      wr(5'h1f, 4'b0010, 32'h01010101); rd(5'h1f, 32'h00000100, 32'h00ffff00);
      wr(5'h10, 4'b1000, 32'h77777777); rd(5'h10, 32'h77000000, 32'hff000000);
      wr(5'h10, 4'b0111, 32'h12345678); rd(5'h10, 32'h77345678, 32'hffffffff);
      wr(5'h03, 4'b0001, 32'h00000011); rd(5'h03, 32'hdeadbe11, 32'hffffffff);
      if (fails == 0) $display("RAM32 gate level: ALL PASSED"); else $display("RAM32 gate level: %0d FAILED", fails);
      $finish;
   end
endmodule
