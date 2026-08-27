// SPDX-License-Identifier: MIT
// MatrixDrive MegaCD FPGA Rev C - Mega Drive cartridge bus bridge.
//
// md_dtack_oe is an enable for an external open-drain/open-collector stage.  The
// FPGA must never drive /DTACK high.

module matrixcd_cart_bridge (
    input  logic        clk,
    input  logic        reset_n,

    input  logic [23:1] md_addr,
    input  logic [15:0] md_data_in,
    input  logic        md_as_n,
    input  logic        md_ce0_n,
    input  logic        md_uds_n,
    input  logic        md_lds_n,
    input  logic        md_rw,

    output logic [15:0] md_data_out,
    output logic        md_data_oe,
    output logic        md_dtack_oe,

    output logic        core_req,
    output logic [23:0] core_addr,
    output logic        core_write,
    output logic [1:0]  core_byte_enable,
    output logic [15:0] core_wdata,
    input  logic [15:0] core_rdata,
    input  logic        core_ack
);

    logic [23:0] byte_addr;
    logic        bios_or_prg_select;
    logic        word_ram_select;
    logic        backup_select;
    logic        gate_reg_select;
    logic        selected;
    logic        cycle_seen;

    always_comb begin
        byte_addr          = {md_addr, 1'b0};
        bios_or_prg_select = !md_ce0_n && (byte_addr <= 24'h03_ffff);
        word_ram_select    = !md_ce0_n &&
                             (byte_addr >= 24'h20_0000) &&
                             (byte_addr <= 24'h23_ffff);
        backup_select      = (byte_addr >= 24'h60_0000) &&
                             (byte_addr <= 24'h60_7fff);
        gate_reg_select    = (byte_addr >= 24'ha1_2000) &&
                             (byte_addr <= 24'ha1_20ff);
        selected           = !md_as_n &&
                             (bios_or_prg_select || word_ram_select ||
                              backup_select || gate_reg_select);
    end

    always_ff @(posedge clk) begin
        if (!reset_n) begin
            md_data_out      <= 16'h0000;
            md_data_oe       <= 1'b0;
            md_dtack_oe      <= 1'b0;
            core_req         <= 1'b0;
            core_addr        <= 24'h000000;
            core_write       <= 1'b0;
            core_byte_enable <= 2'b00;
            core_wdata       <= 16'h0000;
            cycle_seen       <= 1'b0;
        end else begin
            // /AS ending releases every cartridge-bus output.  An unfinished
            // request is abandoned so that a late core_ack cannot acknowledge
            // a later bus cycle.
            if (md_as_n) begin
                md_data_oe  <= 1'b0;
                md_dtack_oe <= 1'b0;
                core_req    <= 1'b0;
                cycle_seen  <= 1'b0;
            end else begin
                if (selected && !cycle_seen) begin
                    core_req         <= 1'b1;
                    core_addr        <= byte_addr;
                    core_write       <= !md_rw;
                    core_byte_enable <= {!md_uds_n, !md_lds_n};
                    core_wdata       <= md_data_in;
                    cycle_seen       <= 1'b1;
                end

                if (core_req && core_ack) begin
                    core_req    <= 1'b0;
                    md_dtack_oe <= 1'b1;
                    if (!core_write) begin
                        md_data_out <= core_rdata;
                        md_data_oe  <= 1'b1;
                    end else begin
                        md_data_oe <= 1'b0;
                    end
                end
            end
        end
    end

endmodule
