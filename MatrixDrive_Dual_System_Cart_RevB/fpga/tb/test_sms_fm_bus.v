`timescale 1ns/1ps

module test_sms_fm_bus;
    reg clk = 1'b0;
    always #35 clk = ~clk;

    reg reset_n = 1'b0;
    reg core_ready = 1'b0;
    reg sms_mode = 1'b1;
    reg usb_mode = 1'b0;
    reg [7:0] sms_a = 8'h00;
    reg [7:0] sms_data_in = 8'h00;
    reg sms_iorq_n = 1'b1;
    reg sms_wr_n = 1'b1;
    reg sms_rd_n = 1'b1;

    wire [7:0] sms_data_out;
    wire sms_data_oe;
    wire [7:0] opll_data;
    wire opll_a0;
    wire opll_cs_n;
    wire opll_wr_n;
    wire [2:0] detect_reg;
    wire fm_enable;

    integer core_write_count = 0;
    reg opll_wr_n_q = 1'b1;

    sms_fm_bus dut (
        .clk(clk), .reset_n(reset_n), .core_ready(core_ready),
        .sms_mode(sms_mode), .usb_mode(usb_mode), .sms_a(sms_a),
        .sms_data_in(sms_data_in), .sms_iorq_n(sms_iorq_n),
        .sms_wr_n(sms_wr_n), .sms_rd_n(sms_rd_n),
        .sms_data_out(sms_data_out), .sms_data_oe(sms_data_oe),
        .opll_data(opll_data), .opll_a0(opll_a0),
        .opll_cs_n(opll_cs_n), .opll_wr_n(opll_wr_n),
        .detect_reg(detect_reg), .fm_enable(fm_enable)
    );

    always @(posedge clk) begin
        opll_wr_n_q <= opll_wr_n;
        if (opll_wr_n_q && !opll_wr_n)
            core_write_count <= core_write_count + 1;
    end

    task io_write;
        input [7:0] port;
        input [7:0] value;
        begin
            @(negedge clk);
            sms_a = port;
            sms_data_in = value;
            sms_iorq_n = 1'b0;
            sms_wr_n = 1'b0;
            repeat (6) @(negedge clk);
            sms_wr_n = 1'b1;
            sms_iorq_n = 1'b1;
            repeat (8) @(negedge clk);
        end
    endtask

    task memory_write;
        input [7:0] low_address;
        input [7:0] value;
        begin
            @(negedge clk);
            sms_a = low_address;
            sms_data_in = value;
            sms_iorq_n = 1'b1;
            sms_wr_n = 1'b0;
            repeat (6) @(negedge clk);
            sms_wr_n = 1'b1;
            repeat (8) @(negedge clk);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        reset_n = 1'b1;
        core_ready = 1'b1;
        repeat (4) @(negedge clk);

        // Reset-compatible F2 value is FF and FM starts enabled.
        sms_a = 8'hF2;
        sms_iorq_n = 1'b0;
        sms_rd_n = 1'b0;
        #1;
        if (!sms_data_oe || sms_data_out !== 8'hFF || !fm_enable)
            $fatal(1, "bad reset F2 read");
        sms_rd_n = 1'b1;
        sms_iorq_n = 1'b1;

        // The /IORQ qualification prevents a normal memory write whose low
        // address happens to be F2 from changing the detection register.
        memory_write(8'hF2, 8'h00);
        if (detect_reg !== 3'b111 || core_write_count != 0)
            $fatal(1, "memory write leaked into FM decode");

        io_write(8'hF0, 8'h20);
        if (core_write_count != 1 || opll_data !== 8'h20 || opll_a0 !== 1'b0)
            $fatal(1, "F0 register write was not forwarded");

        io_write(8'hF1, 8'h17);
        if (core_write_count != 2 || opll_data !== 8'h17 || opll_a0 !== 1'b1)
            $fatal(1, "F1 data write was not forwarded");

        io_write(8'hF2, 8'h02);
        if (detect_reg !== 3'b010 || fm_enable !== 1'b0 ||
            core_write_count != 2)
            $fatal(1, "F2 write behavior is wrong");

        sms_a = 8'hF2;
        sms_iorq_n = 1'b0;
        sms_rd_n = 1'b0;
        #1;
        if (!sms_data_oe || sms_data_out !== 8'hFA)
            $fatal(1, "bad programmed F2 read");

        sms_mode = 1'b0;
        #1;
        if (sms_data_oe)
            $fatal(1, "FPGA drove data bus in MD mode");
        sms_mode = 1'b1;
        usb_mode = 1'b1;
        #1;
        if (sms_data_oe)
            $fatal(1, "FPGA drove data bus in USB mode");

        $display("sms_fm_bus test passed");
        $finish;
    end
endmodule
