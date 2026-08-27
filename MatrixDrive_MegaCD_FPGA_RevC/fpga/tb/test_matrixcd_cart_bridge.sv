`timescale 1ns/1ps

module test_matrixcd_cart_bridge;
    logic        clk = 1'b0;
    logic        reset_n = 1'b0;
    logic [23:1] md_addr = '0;
    logic [15:0] md_data_in = 16'h0000;
    logic        md_as_n = 1'b1;
    logic        md_ce0_n = 1'b1;
    logic        md_uds_n = 1'b1;
    logic        md_lds_n = 1'b1;
    logic        md_rw = 1'b1;
    logic [15:0] md_data_out;
    logic        md_data_oe;
    logic        md_dtack_oe;
    logic        core_req;
    logic [23:0] core_addr;
    logic        core_write;
    logic [1:0]  core_byte_enable;
    logic [15:0] core_wdata;
    logic [15:0] core_rdata = 16'h0000;
    logic        core_ack = 1'b0;

    matrixcd_cart_bridge dut (.*);

    always #5 clk = ~clk;

    task automatic check(input logic condition, input string message);
        begin
            if (!condition) begin
                $display("FAIL: %s", message);
                $fatal(1);
            end
        end
    endtask

    task automatic begin_cycle(
        input logic [23:0] address,
        input logic        write_cycle,
        input logic [1:0]  byte_enable,
        input logic [15:0] write_data
    );
        begin
            md_addr    = address[23:1];
            md_data_in = write_data;
            md_rw      = !write_cycle;
            md_uds_n   = !byte_enable[1];
            md_lds_n   = !byte_enable[0];
            md_ce0_n   = (address < 24'h40_0000) ? 1'b0 : 1'b1;
            md_as_n    = 1'b0;
            @(posedge clk);
            #1;
        end
    endtask

    task automatic acknowledge(input logic [15:0] read_value);
        begin
            core_rdata = read_value;
            core_ack   = 1'b1;
            @(posedge clk);
            #1;
            core_ack = 1'b0;
        end
    endtask

    task automatic end_cycle;
        begin
            md_as_n  = 1'b1;
            md_ce0_n = 1'b1;
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        reset_n = 1'b1;
        @(posedge clk);
        #1;

        // An unrelated cartridge access must remain invisible.
        begin_cycle(24'h50_0000, 1'b0, 2'b11, 16'h0000);
        check(!core_req, "unrelated address generated a core request");
        check(!md_dtack_oe, "unrelated address asserted /DTACK");
        end_cycle();

        // BIOS/program aperture read.
        begin_cycle(24'h00_1234, 1'b0, 2'b11, 16'h0000);
        check(core_req, "BIOS read did not generate a request");
        check(core_addr == 24'h00_1234, "BIOS address was not preserved");
        check(!core_write, "BIOS read was marked as a write");
        check(core_byte_enable == 2'b11, "read byte enables are wrong");
        check(!md_dtack_oe && !md_data_oe,
              "bridge responded before the core acknowledged");
        acknowledge(16'hcafe);
        check(!core_req, "request remained active after acknowledge");
        check(md_dtack_oe, "/DTACK was not asserted after acknowledge");
        check(md_data_oe && md_data_out == 16'hcafe,
              "read data was not driven after acknowledge");
        end_cycle();
        check(!md_dtack_oe && !md_data_oe,
              "bus outputs were not released at end of cycle");

        // Word RAM write with only the upper byte enabled.
        begin_cycle(24'h20_0002, 1'b1, 2'b10, 16'h5a00);
        check(core_req, "Word RAM write did not generate a request");
        check(core_addr == 24'h20_0002, "Word RAM address was not preserved");
        check(core_write, "Word RAM write was marked as a read");
        check(core_byte_enable == 2'b10, "write byte enables are wrong");
        check(core_wdata == 16'h5a00, "write data was not preserved");
        acknowledge(16'h0000);
        check(md_dtack_oe && !md_data_oe,
              "write acknowledgement drove the data bus incorrectly");
        end_cycle();

        // Mega-CD gate-array register aperture.
        begin_cycle(24'ha1_2020, 1'b0, 2'b01, 16'h0000);
        check(core_req && core_addr == 24'ha1_2020,
              "gate-array register read was not decoded");
        acknowledge(16'h00f1);
        check(md_data_out == 16'h00f1, "gate register data was not returned");
        end_cycle();

        $display("PASS: matrixcd_cart_bridge");
        $finish;
    end

endmodule
