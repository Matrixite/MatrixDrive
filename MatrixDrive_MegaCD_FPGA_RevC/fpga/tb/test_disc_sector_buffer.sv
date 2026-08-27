`timescale 1ns/1ps

module test_disc_sector_buffer;
    logic        clk = 1'b0;
    logic        reset_n = 1'b0;
    logic        fill_begin = 1'b0;
    logic [31:0] fill_lba = 32'h00000000;
    logic [11:0] fill_length = 12'h000;
    logic        fill_valid = 1'b0;
    logic [7:0]  fill_data = 8'h00;
    logic        fill_ready;
    logic        fill_commit = 1'b0;
    logic        fill_error;
    logic        sector_valid;
    logic [31:0] sector_lba;
    logic [11:0] sector_length;
    logic        read_begin = 1'b0;
    logic [31:0] read_lba = 32'h00000000;
    logic [11:0] read_offset = 12'h000;
    logic        read_next = 1'b0;
    logic [7:0]  read_data;
    logic        read_valid;
    logic        read_error;

    disc_sector_buffer dut (.*);

    always #5 clk = ~clk;

    task automatic check(input logic condition, input string message);
        begin
            if (!condition) begin
                $display("FAIL: %s", message);
                $fatal(1);
            end
        end
    endtask

    task automatic pulse_fill_begin(input logic [31:0] lba,
                                    input logic [11:0] length);
        begin
            fill_lba    = lba;
            fill_length = length;
            fill_begin  = 1'b1;
            @(posedge clk);
            #1;
            fill_begin = 1'b0;
        end
    endtask

    task automatic send_byte(input logic [7:0] value);
        begin
            check(fill_ready, "buffer was not ready for a declared byte");
            fill_data  = value;
            fill_valid = 1'b1;
            @(posedge clk);
            #1;
            fill_valid = 1'b0;
        end
    endtask

    task automatic pulse_commit;
        begin
            fill_commit = 1'b1;
            @(posedge clk);
            #1;
            fill_commit = 1'b0;
        end
    endtask

    task automatic start_read(input logic [31:0] lba,
                              input logic [11:0] offset);
        begin
            read_lba    = lba;
            read_offset = offset;
            read_begin  = 1'b1;
            @(posedge clk);
            #1;
            read_begin = 1'b0;
        end
    endtask

    task automatic get_byte(input logic [7:0] expected);
        begin
            read_next = 1'b1;
            @(posedge clk);
            #1;
            read_next = 1'b0;
            check(read_valid, "read request did not return a byte");
            check(read_data == expected, "sector byte did not match");
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        reset_n = 1'b1;
        @(posedge clk);
        #1;

        pulse_fill_begin(32'd150, 12'd4);
        check(fill_ready, "valid fill did not become ready");
        send_byte(8'ha0);
        send_byte(8'ha1);
        send_byte(8'ha2);
        send_byte(8'ha3);
        check(!fill_ready, "buffer accepted bytes past declared length");
        pulse_commit();
        check(sector_valid, "complete sector did not commit");
        check(sector_lba == 32'd150 && sector_length == 12'd4,
              "committed sector metadata is wrong");

        start_read(32'd150, 12'd0);
        check(!read_error, "valid sector read was rejected");
        get_byte(8'ha0);
        get_byte(8'ha1);
        get_byte(8'ha2);
        get_byte(8'ha3);

        start_read(32'd151, 12'd0);
        check(read_error, "wrong-LBA read did not report an error");

        pulse_fill_begin(32'd200, 12'd2);
        send_byte(8'h55);
        pulse_commit();
        check(fill_error, "short sector commit did not report an error");
        check(!sector_valid, "short sector was exposed as valid");

        pulse_fill_begin(32'd300, 12'd2353);
        check(fill_error, "oversize sector was accepted");
        check(!fill_ready, "oversize sector enabled writes");

        $display("PASS: disc_sector_buffer");
        $finish;
    end

endmodule
