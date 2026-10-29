`timescale 1ns / 1ps
module tb_ram32;
   reg clk = 0; always #22.5 clk = ~clk;
   reg en = 1; reg [3:0] we = 0; reg [4:0] a = 0; reg [31:0] di = 0; wire [31:0] dout;
   supply1 vpwr; supply0 vgnd;
   RAM32 ram (.CLK(clk), .EN0(en), .VPWR(vpwr), .VGND(vgnd), .A0(a), .Di0(di), .Do0(dout), .WE0(we));
   // word 17 (0x11) byte 0 bit 0: the clock gate and the latch
   wire gclk = ram.\SLICE_16[1].RAM16.SLICE[0].RAM8.WORD[1].W.BYTE[0].B.genblk1.CG .Q;
   wire e    = ram.\SLICE_16[1].RAM16.SLICE[0].RAM8.WORD[1].W.BYTE[0].B.genblk1.CG .E;
   wire cgclk= ram.\SLICE_16[1].RAM16.SLICE[0].RAM8.WORD[1].W.BYTE[0].B.genblk1.CG .CLK;
   wire lq   = ram.\SLICE_16[1].RAM16.SLICE[0].RAM8.WORD[1].W.BYTE[0].B.BIT[0].genblk1.STORAGE .Q;
   wire ld   = ram.\SLICE_16[1].RAM16.SLICE[0].RAM8.WORD[1].W.BYTE[0].B.BIT[0].genblk1.STORAGE .D;
   wire le   = ram.\SLICE_16[1].RAM16.SLICE[0].RAM8.WORD[1].W.BYTE[0].B.BIT[0].genblk1.STORAGE .E;
   always @(gclk or e or cgclk or lq or ld or le or clk) $display("%7.1f clk %b | CG.CLK %b E %b GCLK %b | latch E %b D %b Q %b | we %b a %h", $realtime, clk, cgclk, e, gclk, le, ld, lq, we, a);
   initial begin
      #150;
      $display("-- WE/Di set right after the posedge (as the cache's flops do), one clock");
      @(posedge clk); #1; a = 5'h11; we = 4'b1111; di = 32'hcafef00d; @(posedge clk); #1; we = 0;
      @(negedge clk); @(negedge clk); #1; $display("  read 11 -> %h", dout);
      $finish;
   end
endmodule
