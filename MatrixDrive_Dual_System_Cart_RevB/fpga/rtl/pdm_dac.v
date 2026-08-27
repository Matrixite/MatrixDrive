// First-order pulse-density DAC.  Signed zero maps to 50% duty so the
// mandatory AC-coupled analog stage sees no DC audio component.
module pdm_dac (
    input  wire               clk,
    input  wire               reset_n,
    input  wire signed [15:0] sample,
    output reg                pdm_out
);

    reg [15:0] accumulator;
    wire [15:0] unsigned_sample = sample ^ 16'h8000;
    wire [16:0] sum = {1'b0, accumulator} + {1'b0, unsigned_sample};

    initial begin
        accumulator = 16'h0000;
        pdm_out = 1'b0;
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            accumulator <= 16'h0000;
            pdm_out <= 1'b0;
        end else begin
            accumulator <= sum[15:0];
            pdm_out <= sum[16];
        end
    end

endmodule
