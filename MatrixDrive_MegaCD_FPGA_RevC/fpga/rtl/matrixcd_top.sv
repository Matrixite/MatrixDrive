// SPDX-License-Identifier: MIT
// MatrixDrive MegaCD FPGA Rev C integration shell.
//
// This deliberately exposes the Mega-CD core-side transaction interface.  A
// compatible open-source core is integrated at this boundary in Phase 2.

module matrixcd_top (
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
    input  logic        core_ack,

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

    matrixcd_cart_bridge bridge (
        .clk(clk),
        .reset_n(reset_n),
        .md_addr(md_addr),
        .md_data_in(md_data_in),
        .md_as_n(md_as_n),
        .md_ce0_n(md_ce0_n),
        .md_uds_n(md_uds_n),
        .md_lds_n(md_lds_n),
        .md_rw(md_rw),
        .md_data_out(md_data_out),
        .md_data_oe(md_data_oe),
        .md_dtack_oe(md_dtack_oe),
        .core_req(core_req),
        .core_addr(core_addr),
        .core_write(core_write),
        .core_byte_enable(core_byte_enable),
        .core_wdata(core_wdata),
        .core_rdata(core_rdata),
        .core_ack(core_ack)
    );

    disc_sector_buffer sector_buffer (
        .clk(clk),
        .reset_n(reset_n),
        .fill_begin(fill_begin),
        .fill_lba(fill_lba),
        .fill_length(fill_length),
        .fill_valid(fill_valid),
        .fill_data(fill_data),
        .fill_ready(fill_ready),
        .fill_commit(fill_commit),
        .fill_error(fill_error),
        .sector_valid(sector_valid),
        .sector_lba(sector_lba),
        .sector_length(sector_length),
        .read_begin(read_begin),
        .read_lba(read_lba),
        .read_offset(read_offset),
        .read_next(read_next),
        .read_data(read_data),
        .read_valid(read_valid),
        .read_error(read_error)
    );

endmodule
