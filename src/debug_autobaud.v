/*
================================================================================
debug_autobaud:   Debug Auto Baud Rate Detector (the bit period in clocks, since the second chip)

Copyright 2024 by Ken Pettit <pettitkd@gmail.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.

================================================================================
*/

module debug_autobaud
(
   // Timing and reset inputs
   input  wire                clk,              // System clock 
   input  wire                rst_n,            // Active low reset

   input  wire                disabled,         // Input bit to disable
   input  wire                rx1,              // RX input 1
   input  wire                rx2,              // RX input 2
   input  wire                rx3,              // RX input 3
   output reg                 wr,               // Write the baud rate
   output wire [13:0]         div,              // The bit period in clocks
   output reg  [1:0]          rx_sel            // Selected RX input
);

   reg               s_div_found;               // Indicates if division found
   reg [13:0]        s_pulse_width;             // Pulse width in clks
   reg [13:0]        s_bit_div1;                // The last pulse width in clocks
   reg [1:0]         s_agree_cnt;               // Pulses in a row that agreed with the one before (GF180:
                                                // the two older widths the sky130 chips kept are this count)
   reg               s_last_rx1;                // Last registered value of rx
   reg               s_last_rx2;                // Last registered value of rx
   reg               s_last_rx3;                // Last registered value of rx
   reg [1:0]         s_rx_sel;                  // Last registered value of rx
   reg               s_done;
   wire              s_sel_rx;

   // Three pulses in a row agree to within two clocks (an edge lands in a
   // clock either way after the input synchronizer) and are at least 32
   // clocks, the generator's floor: a bit period, exactly (TT07 kept the
   // width over 32, so a bit had to be a multiple of 32 clocks).  The pulse
   // ending now (s_pulse_width + 1 clocks) is compared with the one before
   // it (s_bit_div1) as it ends, and s_agree_cnt counts the agreements in a
   // row: two of them are three pulses alike.  The sky130 chips kept the
   // three widths and compared the latest with both older ones (the same
   // test to within the two-clock jitter); this is 26 flops and a 15-bit
   // subtractor less (GF180.md).
   wire [14:0]       s_diff   = {1'b0, s_pulse_width} + 15'd3 - {1'b0, s_bit_div1};
   wire              s_agree  = s_diff <= 15'd4 && s_pulse_width >= 14'd31;

   assign div = s_bit_div1;                     // The latest pulse
   assign s_sel_rx = s_rx_sel == 2'h1 ? rx1 : s_rx_sel == 2'h2 ? rx2 : s_rx_sel == 2'h3 ? rx3 : 1'b0;

   always @(posedge clk or negedge rst_n)
   begin
      if (~rst_n)
      begin
         s_div_found    <= 1'b0;                // Baud rate not found
         wr             <= 1'b0;
         s_bit_div1     <= 14'h0;
         s_agree_cnt    <= 2'h0;
         s_pulse_width  <= 14'h0;
         s_last_rx1     <= 1'b0;
         s_last_rx2     <= 1'b0;
         s_last_rx3     <= 1'b0;
         rx_sel         <= 2'h0;
         s_rx_sel       <= 2'h0;
         s_done         <= 1'b0;
      end
      else
      begin
         if (s_div_found == 1'b0)
         begin
            // Create an edge detector for rx
            s_last_rx1 <= rx1;
            s_last_rx2 <= rx2;
            s_last_rx3 <= rx3;

            // Test for change on any of the potential RX inputs
            if ((rx1 != s_last_rx1) || (rx2 != s_last_rx2) || (rx3 != s_last_rx3))
            begin
               // Choose the rx_sel
               if (rx1 != s_last_rx1)
                  s_rx_sel <= 2'h1;
               else if (rx2 != s_last_rx2)
                  s_rx_sel <= 2'h2;
               else if (rx3 != s_last_rx3)
                  s_rx_sel <= 2'h3;

               // Test if auto-baud detector is disabled
               if (disabled)
                  s_div_found <= 1'b1;

               // Reset the pulse width counter
               s_pulse_width <= 14'h0;
               
               // If this is a valid pulse, then save it and count it
               // against the one before (an idle gap breaks the run)
               if (s_pulse_width != 14'h3FFF)
               begin
                  // Save the new pulse width (the counter ran from the
                  // clock after the last edge)
                  s_bit_div1  <= s_pulse_width + 1'b1;
                  s_agree_cnt <= s_agree ? (s_agree_cnt == 2'd2 ? 2'd2 : s_agree_cnt + 2'd1) : 2'd0;
               end
               else
                  s_agree_cnt <= 2'h0;
            end
            else
            begin
               // Create a pulse width counter
               if (s_pulse_width != 14'h3FFF)
                  s_pulse_width <= s_pulse_width + 1;

               // Test for 3 equivalent bit periods
               if (s_agree_cnt == 2'd2)
               begin
                  // We found the period
                  s_div_found <= 1'b1;

                  // Write the divisor to the baud rate generator
                  wr <= 1'b1;
               end
            end
         end
         else if (!s_done)
         begin
            // We found the pulse.  Now wait for the end of the data byte
            // before updating rx_sel 
            wr <= 1'b0;

            // If pulse width not max, then track RX changes
            if (s_pulse_width != 14'h3FFF)
            begin
               s_last_rx1 <= rx1;
               s_last_rx2 <= rx2;
               s_last_rx3 <= rx3;
            end

            if ((rx1 != s_last_rx1) || (rx2 != s_last_rx2) || (rx3 != s_last_rx3))
            begin
               // Reset the pulse width counter
               if (!s_done)
                  s_pulse_width <= 14'h0;
            end
            else
            begin
               // Create a pulse width counter
               if (s_pulse_width != 14'h3FFF)
                  s_pulse_width <= s_pulse_width + 1;

               // When pulse_width is max, update rx_sel
               if (disabled || (s_pulse_width == 14'h3FFF && s_sel_rx == 1'b1))
               begin
                  rx_sel <= s_rx_sel;
                  s_done   <= 1'b1;
               end
            end
         end
      end
   end

endmodule

