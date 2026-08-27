`timescale 1ns/1ps

module test_pdm_dac;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg reset_n = 1'b0;
    reg signed [15:0] sample = 16'sd0;
    wire pdm_out;
    integer ones;
    integer i;

    pdm_dac dut(.clk(clk), .reset_n(reset_n), .sample(sample), .pdm_out(pdm_out));

    task measure;
        input signed [15:0] value;
        input integer expected_ones;
        begin
            sample = value;
            reset_n = 1'b0;
            repeat (2) @(posedge clk);
            reset_n = 1'b1;
            ones = 0;
            for (i = 0; i < 256; i = i + 1) begin
                @(negedge clk);
                if (pdm_out)
                    ones = ones + 1;
            end
            if ((ones < expected_ones - 1) || (ones > expected_ones + 1))
                $fatal(1, "PDM density %0d, expected %0d", ones, expected_ones);
        end
    endtask

    initial begin
        measure(16'sd0, 128);
        measure(16'sh4000, 192);
        measure(-16'sh4000, 64);
        $display("pdm_dac test passed");
        $finish;
    end
endmodule
