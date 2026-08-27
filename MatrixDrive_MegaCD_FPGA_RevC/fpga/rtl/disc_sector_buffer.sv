// SPDX-License-Identifier: MIT
// MatrixDrive MegaCD FPGA Rev C - one-sector MCU-to-FPGA handoff buffer.

module disc_sector_buffer #(
    parameter integer MAX_BYTES = 2352
) (
    input  logic        clk,
    input  logic        reset_n,

    input  logic        fill_begin,
    input  logic [31:0] fill_lba,
    input  logic [11:0] fill_length,
    input  logic        fill_valid,
    input  logic [7:0]  fill_data,
    output logic        fill_ready,
    input  logic        fill_commit,
    output logic        fill_error,

    output logic        sector_valid,
    output logic [31:0] sector_lba,
    output logic [11:0] sector_length,

    input  logic        read_begin,
    input  logic [31:0] read_lba,
    input  logic [11:0] read_offset,
    input  logic        read_next,
    output logic [7:0]  read_data,
    output logic        read_valid,
    output logic        read_error
);

    logic [7:0]  memory [0:MAX_BYTES-1];
    logic        filling;
    logic [31:0] pending_lba;
    logic [11:0] pending_length;
    logic [11:0] fill_count;
    logic        reading;
    logic [11:0] read_pointer;

    always_comb begin
        fill_ready = filling && (fill_count < pending_length) &&
                     (fill_count < MAX_BYTES);
    end

    always_ff @(posedge clk) begin
        if (!reset_n) begin
            filling       <= 1'b0;
            pending_lba   <= 32'h00000000;
            pending_length <= 12'h000;
            fill_count    <= 12'h000;
            fill_error    <= 1'b0;
            sector_valid  <= 1'b0;
            sector_lba    <= 32'h00000000;
            sector_length <= 12'h000;
            reading       <= 1'b0;
            read_pointer  <= 12'h000;
            read_data     <= 8'h00;
            read_valid    <= 1'b0;
            read_error    <= 1'b0;
        end else begin
            fill_error <= 1'b0;
            read_valid <= 1'b0;
            read_error <= 1'b0;

            if (fill_begin) begin
                sector_valid <= 1'b0;
                fill_count   <= 12'h000;
                reading      <= 1'b0;
                if ((fill_length == 0) || (fill_length > MAX_BYTES)) begin
                    filling    <= 1'b0;
                    fill_error <= 1'b1;
                end else begin
                    filling        <= 1'b1;
                    pending_lba    <= fill_lba;
                    pending_length <= fill_length;
                end
            end else if (fill_valid && fill_ready) begin
                memory[fill_count] <= fill_data;
                fill_count         <= fill_count + 1'b1;
            end

            if (fill_commit) begin
                if (filling && (fill_count == pending_length)) begin
                    filling       <= 1'b0;
                    sector_valid  <= 1'b1;
                    sector_lba    <= pending_lba;
                    sector_length <= pending_length;
                end else begin
                    fill_error <= 1'b1;
                end
            end

            if (read_begin) begin
                if (sector_valid && (read_lba == sector_lba) &&
                    (read_offset < sector_length)) begin
                    reading      <= 1'b1;
                    read_pointer <= read_offset;
                end else begin
                    reading    <= 1'b0;
                    read_error <= 1'b1;
                end
            end else if (read_next) begin
                if (reading && (read_pointer < sector_length)) begin
                    read_data  <= memory[read_pointer];
                    read_valid <= 1'b1;
                    if (read_pointer + 1'b1 >= sector_length) begin
                        reading <= 1'b0;
                    end else begin
                        read_pointer <= read_pointer + 1'b1;
                    end
                end else begin
                    read_error <= 1'b1;
                end
            end
        end
    end

endmodule
