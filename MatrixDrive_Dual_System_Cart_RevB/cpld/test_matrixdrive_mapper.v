// SPDX-License-Identifier: MIT
`timescale 1ns/1ps

module test_matrixdrive_mapper;
    reg [20:0] cart_a;
    reg [7:0] data_in;
    reg ce0_n;
    reg cas0_n;
    reg cas2_n;
    reg lwr_n;
    reg reset_n;
    reg sms_mode;
    reg codemasters_mapper;
    reg usb_mode;
    wire [20:0] rom_a;
    wire rom_ce_n;
    wire rom_oe_n;
    wire fram_a13;
    wire fram_a14;
    wire fram_ce_n;
    wire fram_hi_ce_n;
    wire md_fram_ce_n;
    wire fram_oe_n;
    wire fram_we_n;
    wire md_high_disable;

    matrixdrive_mapper dut (
        .cart_a(cart_a), .data_in(data_in), .ce0_n(ce0_n),
        .cas0_n(cas0_n), .cas2_n(cas2_n), .lwr_n(lwr_n),
        .reset_n(reset_n), .sms_mode(sms_mode),
        .codemasters_mapper(codemasters_mapper), .usb_mode(usb_mode),
        .rom_a(rom_a), .rom_ce_n(rom_ce_n), .rom_oe_n(rom_oe_n),
        .fram_a13(fram_a13), .fram_a14(fram_a14),
        .fram_ce_n(fram_ce_n), .fram_hi_ce_n(fram_hi_ce_n),
        .md_fram_ce_n(md_fram_ce_n),
        .fram_oe_n(fram_oe_n), .fram_we_n(fram_we_n),
        .md_high_disable(md_high_disable)
    );

    task set_address(input [15:0] address);
        begin
            cart_a = {5'b00000, address};
            ce0_n = (address < 16'h8000) ? 1'b0 : 1'b1;
            cas2_n = ((address >= 16'h8000) && (address < 16'hc000)) ?
                     1'b0 : 1'b1;
            cas0_n = 1'b0;
            #1;
        end
    endtask

    task write_cycle(input [15:0] address, input [7:0] value);
        begin
            set_address(address);
            data_in = value;
            lwr_n = 1'b0;
            #1;
            lwr_n = 1'b1;
            #1;
        end
    endtask

    task apply_reset;
        begin
            reset_n = 1'b0;
            #1;
            reset_n = 1'b1;
            #1;
        end
    endtask

    task check(input condition, input [8*80-1:0] message);
        begin
            if (!condition) begin
                $display("FAIL: %0s", message);
                $fatal(1);
            end
        end
    endtask

    initial begin
        cart_a = 0;
        data_in = 0;
        ce0_n = 1;
        cas0_n = 1;
        cas2_n = 1;
        lwr_n = 1;
        reset_n = 1;
        sms_mode = 1;
        codemasters_mapper = 0;
        usb_mode = 0;
        apply_reset();

        set_address(16'h0000);
        check(rom_a == 21'h000000, "Sega reset slot 0");
        set_address(16'h4000);
        check(rom_a == 21'h004000, "Sega reset slot 1");
        set_address(16'h8000);
        check(rom_a == 21'h008000, "Sega reset slot 2");

        write_cycle(16'hfffd, 8'h25);
        set_address(16'h0000);
        check(rom_a == 21'h000000, "Sega fixed first 1 KiB");
        set_address(16'h0400);
        check(rom_a == ((21'h25 << 14) | 21'h0400), "Sega bank 0");

        write_cycle(16'hfffc, 8'h0c);
        set_address(16'h8000);
        check(rom_ce_n && !fram_ce_n && fram_hi_ce_n && md_fram_ce_n,
              "Sega low FRAM selected");
        check(!fram_a13 && fram_a14, "Sega FRAM bank 1 lower address");
        set_address(16'hbfff);
        check(fram_a13 && fram_a14, "Sega FRAM bank 1 upper address");

        codemasters_mapper = 1;
        apply_reset();
        set_address(16'h8000);
        check(rom_a == 21'h000000, "Codemasters reset slot 2 is bank 0");

        write_cycle(16'h0000, 8'h05);
        write_cycle(16'h4000, 8'h03);
        write_cycle(16'h8000, 8'h06);
        set_address(16'h0000);
        check(rom_a == (21'h05 << 14), "Codemasters has no fixed window");
        set_address(16'h4000);
        check(rom_a == (21'h03 << 14), "Codemasters slot 1 bank");
        set_address(16'h8000);
        check(rom_a == (21'h06 << 14), "Codemasters slot 2 bank");

        write_cycle(16'h4000, 8'h87);
        set_address(16'h4000);
        check(rom_a == (21'h03 << 14),
              "RAM enable preserves Codemasters slot 1");
        set_address(16'h8000);
        check(!rom_ce_n && fram_ce_n && fram_hi_ce_n && md_fram_ce_n,
              "Codemasters ROM remains at 8000-9FFF");
        set_address(16'ha000);
        check(rom_ce_n && fram_ce_n && !fram_hi_ce_n && md_fram_ce_n,
              "Codemasters high FRAM selected at A000-BFFF");
        check(fram_a13 && fram_a14, "Codemasters FRAM bank 7 address bits");

        write_cycle(16'h4000, 8'h04);
        set_address(16'ha000);
        check(!rom_ce_n && fram_ce_n && fram_hi_ce_n,
              "Codemasters RAM disable restores ROM");
        set_address(16'h4000);
        check(rom_a == (21'h04 << 14),
              "Codemasters RAM disable updates slot 1");

        // MD/32X linear / Sonic 2 lock-on profile.
        sms_mode = 0;
        codemasters_mapper = 0;
        cart_a = 21'h012345;
        ce0_n = 0;
        cas0_n = 0;
        #1;
        check(rom_a == 21'h012345 && !rom_ce_n && !rom_oe_n,
              "Mega Drive/32X pass-through");
        check(md_fram_ce_n && !md_high_disable,
              "MD linear profile keeps dedicated FRAM disabled");
        cart_a = 21'h1fffff;
        #1;
        check(rom_a == 21'h1fffff && !rom_ce_n && !rom_oe_n,
              "32X top of 4 MiB cartridge space remains linear ROM");

        // SW4 high in MD mode supplies the Sonic 3 & Knuckles save window.
        codemasters_mapper = 1;
        cart_a = 21'h0fffff;
        #1;
        check(!rom_ce_n && md_fram_ce_n && !md_high_disable,
              "Address below Sonic 3 save window remains ROM");
        cart_a = 21'h100000;
        lwr_n = 1;
        #1;
        check(rom_ce_n && rom_oe_n && !md_fram_ce_n,
              "Sonic 3 save starts at CPU byte address 200001");
        check(!fram_oe_n && fram_we_n && md_high_disable,
              "Sonic 3 FRAM read disables MD high data byte");
        cart_a = 21'h101fff;
        #1;
        check(!md_fram_ce_n, "Sonic 3 save includes CPU address 203FFF");
        lwr_n = 0;
        #1;
        check(!fram_we_n && md_high_disable,
              "Sonic 3 odd-byte FRAM write");
        lwr_n = 1;
        cart_a = 21'h102000;
        #1;
        check(!rom_ce_n && md_fram_ce_n && !md_high_disable,
              "Address above Sonic 3 save window returns to ROM");

        usb_mode = 1;
        #1;
        check((rom_ce_n === 1'bz) && (fram_ce_n === 1'bz) &&
              (fram_hi_ce_n === 1'bz) && (md_fram_ce_n === 1'bz),
              "USB mode tri-states memory controls");
        check(md_high_disable, "USB mode requests high-data isolation");

        $display("matrixdrive_mapper RTL simulation passed");
        $finish;
    end
endmodule
