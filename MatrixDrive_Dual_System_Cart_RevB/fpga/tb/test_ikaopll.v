`timescale 1ns/1ps

// Direct, self-checking harness for the vendored IKAOPLL YM2413 core.
//
// The MatrixDrive top-level integration has separate tests for its F0/F1/F2
// bus front-end and PDM converter.  This harness deliberately bypasses those
// wrappers so a regression in the actual FM core, its clock enable, register
// write timing, melodic path, or rhythm path fails independently.
module test_ikaopll;
    localparam integer SAMPLE_COUNT = 256;
    localparam [31:0] SILENCE_SIGNATURE = 32'ha7b537c5;
    localparam [31:0] TONE_SIGNATURE    = 32'h4c628802;
    localparam [31:0] RELEASE_SIGNATURE = 32'h2dce97db;
    localparam [31:0] RHYTHM_SIGNATURE  = 32'h0a9f551a;

    reg clk = 1'b0;
    always #35 clk = ~clk; // approximately 14.318180 MHz

    reg [1:0] phim_div = 2'd0;
    always @(posedge clk)
        phim_div <= phim_div + 1'b1;
    wire phim_pcen_n = ~(phim_div == 2'd3);

    reg reset_n = 1'b0;
    reg cs_n = 1'b1;
    reg wr_n = 1'b1;
    reg a0 = 1'b0;
    reg [7:0] data_in = 8'h00;

    wire [1:0] data_out;
    wire data_oe;
    wire acc_strobe;
    wire signed [15:0] acc_sample;
    wire unused_xout;
    wire unused_dac_mo;
    wire unused_dac_ro;
    wire unused_imp_sign;
    wire [7:0] unused_imp_mag;
    wire signed [9:0] unused_imp_mo;
    wire signed [9:0] unused_imp_ro;

    IKAOPLL #(
        .FULLY_SYNCHRONOUS        (1),
        .FAST_RESET               (1),
        .ALTPATCH_CONFIG_MODE     (0),
        .USE_PIPELINED_MULTIPLIER (1)
    ) dut (
        .i_XIN_EMUCLK         (clk),
        .o_XOUT               (unused_xout),
        .i_phiM_PCEN_n        (phim_pcen_n),
        .i_IC_n               (reset_n),
        .i_ALTPATCH_EN        (1'b0),
        .i_CS_n               (cs_n),
        .i_WR_n               (wr_n),
        .i_A0                 (a0),
        .i_D                  (data_in),
        .o_D                  (data_out),
        .o_D_OE               (data_oe),
        .o_DAC_EN_MO          (unused_dac_mo),
        .o_DAC_EN_RO          (unused_dac_ro),
        .o_IMP_NOFLUC_SIGN    (unused_imp_sign),
        .o_IMP_NOFLUC_MAG     (unused_imp_mag),
        .o_IMP_FLUC_SIGNED_MO (unused_imp_mo),
        .o_IMP_FLUC_SIGNED_RO (unused_imp_ro),
        .i_ACC_SIGNED_MOVOL   (5'sd2),
        .i_ACC_SIGNED_ROVOL   (5'sd3),
        .o_ACC_SIGNED_STRB    (acc_strobe),
        .o_ACC_SIGNED         (acc_sample)
    );

    task bus_write;
        input select_data;
        input [7:0] value;
        begin
            @(negedge clk);
            a0 = select_data;
            data_in = value;
            cs_n = 1'b0;
            wr_n = 1'b0;
            // FULLY_SYNCHRONOUS adds input synchronizers.  Keeping the write
            // active across several phiM enables also makes this exercise the
            // same asynchronous-bus allowance used by the cartridge wrapper.
            repeat (8) @(negedge clk);
            cs_n = 1'b1;
            wr_n = 1'b1;
            // The core serializes register traffic through phiM and phi1
            // enables.  Keep address and data transactions far enough apart
            // that the first synchronized request consumes its latched byte
            // before the next byte is placed on the bus.
            repeat (128) @(negedge clk);
        end
    endtask

    task ym_write;
        input [7:0] address;
        input [7:0] value;
        begin
            bus_write(1'b0, address);
            bus_write(1'b1, value);
            // A D9 register update is serialized across the nine channel
            // slots.  Wait longer than one complete worst-case scan before
            // replacing the address latch with the next register number.
            repeat (512) @(posedge clk);
        end
    endtask

    task discard_samples;
        input integer count;
        integer n;
        begin
            for (n = 0; n < count; n = n + 1)
                @(posedge acc_strobe);
        end
    endtask

    task capture_stats;
        input integer count;
        output integer nonzero_count;
        output integer min_value;
        output integer max_value;
        output integer absolute_sum;
        output integer zero_crossings;
        output reg [31:0] signature;
        integer n;
        integer value;
        integer previous;
        begin
            nonzero_count = 0;
            min_value = 32767;
            max_value = -32768;
            absolute_sum = 0;
            zero_crossings = 0;
            signature = 32'h811c9dc5;
            previous = 0;

            for (n = 0; n < count; n = n + 1) begin
                @(posedge acc_strobe);
                #1;
                if (^acc_sample === 1'bx)
                    $fatal(1, "IKAOPLL emitted an unknown audio sample");

                value = $signed(acc_sample);
                if (value != 0)
                    nonzero_count = nonzero_count + 1;
                if (value < min_value)
                    min_value = value;
                if (value > max_value)
                    max_value = value;
                if (value < 0)
                    absolute_sum = absolute_sum - value;
                else
                    absolute_sum = absolute_sum + value;
                if (n != 0 && ((value < 0 && previous >= 0) ||
                               (value >= 0 && previous < 0)))
                    zero_crossings = zero_crossings + 1;
                previous = value;

                // FNV-1a over both sample bytes gives a compact deterministic
                // regression signature without storing a large golden waveform.
                signature = (signature ^ {24'd0, acc_sample[7:0]}) * 32'h01000193;
                signature = (signature ^ {24'd0, acc_sample[15:8]}) * 32'h01000193;
            end
        end
    endtask

    integer silent_nonzero;
    integer silent_min;
    integer silent_max;
    integer silent_sum;
    integer silent_crossings;
    reg [31:0] silent_signature;

    integer tone_nonzero;
    integer tone_min;
    integer tone_max;
    integer tone_sum;
    integer tone_crossings;
    reg [31:0] tone_signature;

    integer release_nonzero;
    integer release_min;
    integer release_max;
    integer release_sum;
    integer release_crossings;
    reg [31:0] release_signature;

    integer rhythm_nonzero;
    integer rhythm_min;
    integer rhythm_max;
    integer rhythm_sum;
    integer rhythm_crossings;
    reg [31:0] rhythm_signature;

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/test_ikaopll.vcd");
            $dumpvars(0, test_ikaopll);
        end

        // FAST_RESET still needs enough active emulation clocks to flush the
        // complete core.  This exceeds both the core minimum and top-level hold.
        repeat (1024) @(posedge clk);
        reset_n = 1'b1;
        repeat (256) @(posedge clk);

        capture_stats(64, silent_nonzero, silent_min, silent_max, silent_sum,
                      silent_crossings, silent_signature);
        if (silent_nonzero != 0 || silent_sum != 0 ||
            silent_signature != SILENCE_SIGNATURE)
            $fatal(1, "reset output mismatch: nonzero=%0d sum=%0d signature=%08x",
                   silent_nonzero, silent_sum, silent_signature);

        // Channel 0: built-in violin patch, maximum level, middle register
        // range, then key on.  This exercises instrument ROM, phase/envelope
        // generators, operator feedback, melodic DAC, accumulator and mixer.
        ym_write(8'h30, 8'h10);
        ym_write(8'h10, 8'h98);
        ym_write(8'h20, 8'h15);
        discard_samples(128);
        capture_stats(SAMPLE_COUNT, tone_nonzero, tone_min, tone_max, tone_sum,
                      tone_crossings, tone_signature);

        if (tone_nonzero < 200 || tone_min >= 0 || tone_max <= 8 ||
            tone_sum < 1000 || tone_crossings < 4 ||
            tone_signature != TONE_SIGNATURE)
            $fatal(1, "melodic output failed: nz=%0d min=%0d max=%0d sum=%0d crossings=%0d",
                   tone_nonzero, tone_min, tone_max, tone_sum, tone_crossings);

        // Key off must move the envelope into release and produce a waveform
        // different from the sustained tone window.
        ym_write(8'h20, 8'h05);
        discard_samples(512);
        capture_stats(SAMPLE_COUNT, release_nonzero, release_min, release_max,
                      release_sum, release_crossings, release_signature);
        if (release_signature != RELEASE_SIGNATURE ||
            release_signature == tone_signature)
            $fatal(1, "key-off output mismatch: signature=%08x",
                   release_signature);

        // Configure channels 6-8 as the YM2413 rhythm voices, set their
        // volumes, enable rhythm mode, and key all five percussion instruments.
        ym_write(8'h16, 8'h20);
        ym_write(8'h17, 8'h50);
        ym_write(8'h18, 8'hc0);
        ym_write(8'h26, 8'h05);
        ym_write(8'h27, 8'h05);
        ym_write(8'h28, 8'h01);
        ym_write(8'h36, 8'h00);
        ym_write(8'h37, 8'h00);
        ym_write(8'h38, 8'h00);
        ym_write(8'h0e, 8'h3f);
        discard_samples(128);
        capture_stats(SAMPLE_COUNT, rhythm_nonzero, rhythm_min, rhythm_max,
                      rhythm_sum, rhythm_crossings, rhythm_signature);

        if (rhythm_nonzero < 200 || rhythm_min >= 0 || rhythm_max <= 8 ||
            rhythm_sum < 1000 || rhythm_crossings < 4 ||
            rhythm_signature == tone_signature ||
            rhythm_signature != RHYTHM_SIGNATURE)
            $fatal(1, "rhythm output failed: nz=%0d min=%0d max=%0d sum=%0d crossings=%0d",
                   rhythm_nonzero, rhythm_min, rhythm_max, rhythm_sum,
                   rhythm_crossings);

        $display("IKAOPLL silence signature: %08x", silent_signature);
        $display("IKAOPLL tone:    sig=%08x min=%0d max=%0d sum=%0d crossings=%0d",
                 tone_signature, tone_min, tone_max, tone_sum, tone_crossings);
        $display("IKAOPLL release: sig=%08x min=%0d max=%0d sum=%0d crossings=%0d",
                 release_signature, release_min, release_max, release_sum,
                 release_crossings);
        $display("IKAOPLL rhythm:  sig=%08x min=%0d max=%0d sum=%0d crossings=%0d",
                 rhythm_signature, rhythm_min, rhythm_max, rhythm_sum,
                 rhythm_crossings);
        $display("IKAOPLL core test passed");
        $finish;
    end

    initial begin
        // A stuck clock/strobe should fail quickly instead of hanging CI.
        #200000000;
        $fatal(1, "IKAOPLL test timeout");
    end
endmodule
