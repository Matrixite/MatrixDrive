// SPDX-License-Identifier: MIT
// MatrixDrive Rev B combinational ROM mux and Sega SMS mapper registers.
// Pin numbers and timing constraints must be assigned and verified for the
// exact ATF1508ASV-15AU100 toolchain before a board is released.

module matrixdrive_mapper (
    input  wire [20:0] cart_a,
    input  wire [7:0]  data_in,
    input  wire        ce0_n,
    input  wire        cas0_n,
    input  wire        cas2_n,
    input  wire        lwr_n,
    input  wire        reset_n,
    input  wire        sms_mode,
    input  wire        usb_mode,
    output wire [20:0] rom_a,
    output wire        rom_ce_n,
    output wire        rom_oe_n,
    output wire        fram_a14,
    output wire        fram_ce_n,
    output wire        fram_oe_n,
    output wire        fram_we_n
);

    reg [7:0] control;
    reg [7:0] bank0;
    reg [7:0] bank1;
    reg [7:0] bank2;

    wire mapper_write = sms_mode && (cart_a[15:2] == 14'h3fff);

    // Capture at the end of a Z80 write cycle, after data has propagated
    // through the low-byte bidirectional translator.
    always @(posedge lwr_n or negedge reset_n) begin
        if (!reset_n) begin
            control <= 8'h00;
            bank0   <= 8'h00;
            bank1   <= 8'h01;
            bank2   <= 8'h02;
        end else if (mapper_write) begin
            case (cart_a[1:0])
                2'b00: control <= data_in; // $FFFC
                2'b01: bank0   <= data_in; // $FFFD
                2'b10: bank1   <= data_in; // $FFFE
                2'b11: bank2   <= data_in; // $FFFF
            endcase
        end
    end

    reg [6:0] selected_bank;
    always @* begin
        if (cart_a[15:10] == 6'b000000)
            selected_bank = 7'h00; // fixed $0000-$03FF
        else begin
            case (cart_a[15:14])
                2'b00: selected_bank = bank0[6:0];
                2'b01: selected_bank = bank1[6:0];
                default: selected_bank = bank2[6:0];
            endcase
        end
    end

    wire sms_slot01 = !cart_a[15] && !ce0_n;
    wire sms_slot2  = (cart_a[15:14] == 2'b10) && !cas2_n;
    wire sms_rom_selected = sms_slot01 || sms_slot2;
    wire sms_save_selected = sms_slot2 && control[3];

    wire [20:0] rom_a_active = sms_mode ?
        {selected_bank, cart_a[13:0]} : cart_a;
    wire rom_ce_active = sms_mode ?
        !(sms_rom_selected && !sms_save_selected) : ce0_n;
    wire rom_oe_active = sms_mode ?
        ((sms_rom_selected && !sms_save_selected) ? cas0_n : 1'b1) : cas0_n;
    wire fram_ce_active = (sms_mode && sms_save_selected) ? 1'b0 : 1'b1;
    wire fram_oe_active = (sms_mode && sms_save_selected) ? cas0_n : 1'b1;
    wire fram_we_active = (sms_mode && sms_save_selected) ? lwr_n : 1'b1;

    // External 10 kOhm pulls hold the memories inactive while these outputs
    // are released for RP2350 ownership in USB programming mode.
    assign rom_a     = usb_mode ? 21'bz : rom_a_active;
    assign rom_ce_n  = usb_mode ? 1'bz : rom_ce_active;
    assign rom_oe_n  = usb_mode ? 1'bz : rom_oe_active;
    assign fram_a14  = usb_mode ? 1'bz : control[2];
    assign fram_ce_n = usb_mode ? 1'bz : fram_ce_active;
    assign fram_oe_n = usb_mode ? 1'bz : fram_oe_active;
    assign fram_we_n = usb_mode ? 1'bz : fram_we_active;

endmodule
