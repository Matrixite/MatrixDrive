// MatrixDrive Master System FM bus front-end.
//
// VA19 on the Mega Drive cartridge edge becomes /IORQ in SMS mode.  The
// translated signal is CART_A18 on Revision B.  It must be part of every
// FM-port decode; address-only decoding would mistake ordinary RAM writes for
// YM2413 traffic.
module sms_fm_bus #(
    parameter integer CORE_WRITE_CYCLES = 4
) (
    input  wire       clk,
    input  wire       reset_n,
    input  wire       core_ready,

    input  wire       sms_mode,
    input  wire       usb_mode,
    input  wire [7:0] sms_a,
    input  wire [7:0] sms_data_in,
    input  wire       sms_iorq_n,
    input  wire       sms_wr_n,
    input  wire       sms_rd_n,

    output wire [7:0] sms_data_out,
    output wire       sms_data_oe,

    output reg  [7:0] opll_data,
    output reg        opll_a0,
    output reg        opll_cs_n,
    output reg        opll_wr_n,

    output reg  [2:0] detect_reg,
    output wire       fm_enable
);

    localparam integer HOLD_WIDTH =
        (CORE_WRITE_CYCLES <= 1) ? 1 : $clog2(CORE_WRITE_CYCLES + 1);
    localparam [7:0] OPLL_ADDRESS_PORT = 8'hF0;
    localparam [7:0] OPLL_DATA_PORT = 8'hF1;
    localparam [7:0] FM_DETECT_PORT = 8'hF2;

    // Synchronize the cartridge bus into the 14.31818 MHz FPGA clock domain.
    // A Z80 I/O write remains asserted for several of these clocks.  Address
    // and data use the same two-stage pipeline as the controls so they are
    // stable when a new write is recognized.
    reg [7:0] addr_meta;
    reg [7:0] addr_sync;
    reg [7:0] data_meta;
    reg [7:0] data_sync;
    reg [4:0] ctrl_meta;
    reg [4:0] ctrl_sync;
    reg       write_active_q;
    reg [HOLD_WIDTH-1:0] write_hold;

    wire mode_sync   = ctrl_sync[4];
    wire usb_sync    = ctrl_sync[3];
    wire iorq_n_sync = ctrl_sync[2];
    wire wr_n_sync   = ctrl_sync[1];
    wire write_active = mode_sync && !usb_sync && !iorq_n_sync && !wr_n_sync;
    wire new_write = write_active && !write_active_q;

    // F0 is the YM2413 register-address port and F1 is its data port.
    wire synced_opll_port = (addr_sync == OPLL_ADDRESS_PORT) ||
                            (addr_sync == OPLL_DATA_PORT);
    wire synced_detect_port = (addr_sync == FM_DETECT_PORT);

    // F2 is a cartridge-provided compatibility/detection register.  The
    // asynchronous read path is intentional: the console must see the value
    // during the current /RD window, not two FPGA clocks later.
    wire raw_detect_read = sms_mode && !usb_mode && !sms_iorq_n &&
                           !sms_rd_n && (sms_a == FM_DETECT_PORT);
    assign sms_data_oe = raw_detect_read;
    assign sms_data_out = {5'b11111, detect_reg};
    assign fm_enable = detect_reg[0];

    initial begin
        detect_reg = 3'b111;
        opll_data = 8'h00;
        opll_a0 = 1'b0;
        opll_cs_n = 1'b1;
        opll_wr_n = 1'b1;
        addr_meta = 8'h00;
        addr_sync = 8'h00;
        data_meta = 8'h00;
        data_sync = 8'h00;
        ctrl_meta = 5'b00111;
        ctrl_sync = 5'b00111;
        write_active_q = 1'b0;
        write_hold = {HOLD_WIDTH{1'b0}};
    end

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            addr_meta <= 8'h00;
            addr_sync <= 8'h00;
            data_meta <= 8'h00;
            data_sync <= 8'h00;
            ctrl_meta <= 5'b00111;
            ctrl_sync <= 5'b00111;
            write_active_q <= 1'b0;
            write_hold <= {HOLD_WIDTH{1'b0}};
            opll_data <= 8'h00;
            opll_a0 <= 1'b0;
            opll_cs_n <= 1'b1;
            opll_wr_n <= 1'b1;
            detect_reg <= 3'b111;
        end else begin
            addr_meta <= sms_a;
            addr_sync <= addr_meta;
            data_meta <= sms_data_in;
            data_sync <= data_meta;
            ctrl_meta <= {sms_mode, usb_mode, sms_iorq_n, sms_wr_n, sms_rd_n};
            ctrl_sync <= ctrl_meta;
            write_active_q <= write_active;

            if (write_hold != 0) begin
                write_hold <= write_hold - 1'b1;
                if (write_hold == 1) begin
                    opll_cs_n <= 1'b1;
                    opll_wr_n <= 1'b1;
                end
            end

            if (new_write) begin
                if (synced_detect_port) begin
                    detect_reg <= data_sync[2:0];
                end else if (synced_opll_port && core_ready &&
                             (write_hold == 0)) begin
                    opll_data <= data_sync;
                    opll_a0 <= addr_sync[0];
                    opll_cs_n <= 1'b0;
                    opll_wr_n <= 1'b0;
                    write_hold <= CORE_WRITE_CYCLES;
                end
            end
        end
    end

endmodule
