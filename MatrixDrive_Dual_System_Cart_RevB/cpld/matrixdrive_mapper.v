// SPDX-License-Identifier: MIT
// MatrixDrive Rev B ROM mux, SMS mappers, and Sonic & Knuckles upper-cart save.
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
    input  wire        codemasters_mapper,
    input  wire        usb_mode,
    output wire [20:0] rom_a,
    output wire        rom_ce_n,
    output wire        rom_oe_n,
    output wire        fram_a13,
    output wire        fram_a14,
    output wire        fram_ce_n,
    output wire        fram_hi_ce_n,
    output wire        md_fram_ce_n,
    output wire        fram_oe_n,
    output wire        fram_we_n,
    output wire        md_high_disable
);

    reg [7:0] sega_control;
    reg [7:0] sega_bank0;
    reg [7:0] sega_bank1;
    reg [7:0] sega_bank2;

    reg [7:0] codies_bank0;
    reg [7:0] codies_bank1;
    reg [7:0] codies_bank2;
    reg       codies_ram_enabled;
    reg [2:0] codies_ram_bank;

    wire sega_profile = sms_mode && !codemasters_mapper;
    wire codies_profile = sms_mode && codemasters_mapper;

    // SW4 is dual-purpose. In SMS mode it selects Codemasters. In MD mode its
    // high position enables the Sonic 3 odd-byte save window used through the
    // Sonic & Knuckles upper cartridge slot.
    wire md_s3_save_profile = !sms_mode && codemasters_mapper;

    wire sega_mapper_write = sega_profile &&
                             (cart_a[15:2] == 14'h3fff);
    wire codies_mapper_write = codies_profile &&
                               ((cart_a[15:0] == 16'h0000) ||
                                (cart_a[15:0] == 16'h4000) ||
                                (cart_a[15:0] == 16'h8000));

    // Capture at the end of a Z80 write cycle, after data has propagated
    // through the low-byte bidirectional translator.
    always @(posedge lwr_n or negedge reset_n) begin
        if (!reset_n) begin
            sega_control       <= 8'h00;
            sega_bank0         <= 8'h00;
            sega_bank1         <= 8'h01;
            sega_bank2         <= 8'h02;
            codies_bank0       <= 8'h00;
            codies_bank1       <= 8'h01;
            codies_bank2       <= 8'h00;
            codies_ram_enabled <= 1'b0;
            codies_ram_bank    <= 3'b000;
        end else if (sega_mapper_write) begin
            case (cart_a[1:0])
                2'b00: sega_control <= data_in; // $FFFC
                2'b01: sega_bank0   <= data_in; // $FFFD
                2'b10: sega_bank1   <= data_in; // $FFFE
                2'b11: sega_bank2   <= data_in; // $FFFF
            endcase
        end else if (codies_mapper_write) begin
            case (cart_a[15:0])
                16'h0000: codies_bank0 <= data_in;
                16'h4000: begin
                    if (data_in[7]) begin
                        codies_ram_enabled <= 1'b1;
                        codies_ram_bank    <= data_in[2:0];
                    end else begin
                        codies_ram_enabled <= 1'b0;
                        codies_bank1       <= data_in;
                    end
                end
                16'h8000: codies_bank2 <= data_in;
            endcase
        end
    end

    reg [6:0] selected_bank;
    always @* begin
        if (codies_profile) begin
            case (cart_a[15:14])
                2'b00: selected_bank = codies_bank0[6:0];
                2'b01: selected_bank = codies_bank1[6:0];
                default: selected_bank = codies_bank2[6:0];
            endcase
        end else if (cart_a[15:10] == 6'b000000) begin
            selected_bank = 7'h00; // Sega fixed $0000-$03FF window
        end else begin
            case (cart_a[15:14])
                2'b00: selected_bank = sega_bank0[6:0];
                2'b01: selected_bank = sega_bank1[6:0];
                default: selected_bank = sega_bank2[6:0];
            endcase
        end
    end

    wire sms_slot01 = !cart_a[15] && !ce0_n;
    wire sms_slot2  = (cart_a[15:14] == 2'b10) && !cas2_n;
    wire sms_rom_selected = sms_slot01 || sms_slot2;
    wire sega_save_selected = sega_profile && sms_slot2 &&
                              sega_control[3];
    wire codies_save_selected = codies_profile && sms_slot2 &&
                                cart_a[13] && codies_ram_enabled;
    wire sms_save_selected = sega_save_selected || codies_save_selected;

    // VA1 is cart_a[0] in MD mode, so CPU byte addresses $200001-$203FFF
    // correspond to word addresses $100000-$101FFF. /LWR selects the odd byte.
    wire md_s3_save_selected = md_s3_save_profile && !ce0_n &&
                               (cart_a[20:13] == 8'h80);
    wire any_save_selected = sms_save_selected || md_s3_save_selected;

    // Sega supplies 2 x 16 KiB through A14. Codemasters supplies 8 x 8 KiB
    // through A15:A13, covering the complete 64 KiB SMS FRAM address space.
    wire fram_a13_active = codies_profile ? codies_ram_bank[0] :
                           (sega_profile ? cart_a[13] : 1'b0);
    wire fram_a14_active = codies_profile ? codies_ram_bank[1] :
                           (sega_profile ? sega_control[2] : 1'b0);
    wire fram_high_active = codies_profile && codies_ram_bank[2];

    wire [20:0] rom_a_active = sms_mode ?
        {selected_bank, cart_a[13:0]} : cart_a;
    wire rom_ce_active = sms_mode ?
        !(sms_rom_selected && !sms_save_selected) :
        (md_s3_save_selected ? 1'b1 : ce0_n);
    wire rom_oe_active = sms_mode ?
        ((sms_rom_selected && !sms_save_selected) ? cas0_n : 1'b1) :
        (md_s3_save_selected ? 1'b1 : cas0_n);

    wire fram_ce_active = (sms_save_selected && !fram_high_active) ?
                          1'b0 : 1'b1;
    wire fram_hi_ce_active = (sms_save_selected && fram_high_active) ?
                             1'b0 : 1'b1;
    wire md_fram_ce_active = md_s3_save_selected ? 1'b0 : 1'b1;
    wire fram_oe_active = any_save_selected ? cas0_n : 1'b1;
    wire fram_we_active = any_save_selected ? lwr_n : 1'b1;

    // External pulls hold memories inactive while shared outputs are released
    // for RP2350 ownership in USB programming mode.
    assign rom_a        = usb_mode ? 21'bz : rom_a_active;
    assign rom_ce_n     = usb_mode ? 1'bz : rom_ce_active;
    assign rom_oe_n     = usb_mode ? 1'bz : rom_oe_active;
    assign fram_a13     = usb_mode ? 1'bz : fram_a13_active;
    assign fram_a14     = usb_mode ? 1'bz : fram_a14_active;
    assign fram_ce_n    = usb_mode ? 1'bz : fram_ce_active;
    assign fram_hi_ce_n = usb_mode ? 1'bz : fram_hi_ce_active;
    assign md_fram_ce_n = usb_mode ? 1'bz : md_fram_ce_active;
    assign fram_oe_n    = usb_mode ? 1'bz : fram_oe_active;
    assign fram_we_n    = usb_mode ? 1'bz : fram_we_active;

    // U19 translates this to the 5 V U15 gate. A known high during USB
    // coexistence keeps the upper data translator disabled.
    assign md_high_disable = usb_mode ? 1'b1 : md_s3_save_selected;

endmodule
