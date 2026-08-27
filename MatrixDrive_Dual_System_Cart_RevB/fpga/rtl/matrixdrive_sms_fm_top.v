// MatrixDrive optional FPGA Master System FM block.
//
// Target clock: 14.318180 MHz.  A one-in-four clock enable gives IKAOPLL the
// 3.579545 MHz phiM rate used by NTSC Master System hardware.  A separate PAL
// clock population option is documented in fpga/README.md.
module matrixdrive_sms_fm_top (
    input  wire       clk_14m318,
    input  wire       reset_n,
    input  wire       sms_mode,
    input  wire       usb_mode,

    input  wire [7:0] cart_a,
    input  wire       cart_a18_iorq_n,
    input  wire       lwr_n,
    input  wire       cas0_n,
    inout  wire [7:0] mem_d,

    output wire       fm_pdm,
    output wire       fm_active,
    output wire       fm_core_ready
);

    // Hold the core in reset after FPGA configuration even if console /MRES
    // was released before configuration completed.  1024 clocks is about
    // 71.5 us and comfortably exceeds IKAOPLL's FAST_RESET requirement.
    reg [9:0] startup_count;
    initial startup_count = 10'd0;
    always @(posedge clk_14m318 or negedge reset_n) begin
        if (!reset_n)
            startup_count <= 10'd0;
        else if (!(&startup_count))
            startup_count <= startup_count + 1'b1;
    end
    assign fm_core_ready = &startup_count;
    wire core_reset_n = reset_n && fm_core_ready;

    // Divide the 14.31818 MHz emulation clock with a clock enable.  The FPGA
    // still has one physical clock domain.
    reg [1:0] phim_div;
    initial phim_div = 2'd0;
    always @(posedge clk_14m318 or negedge reset_n) begin
        if (!reset_n)
            phim_div <= 2'd0;
        else
            phim_div <= phim_div + 1'b1;
    end
    wire phim_pcen_n = ~(phim_div == 2'd3);

    wire [7:0] bus_data_out;
    wire       bus_data_oe;
    wire [7:0] opll_data;
    wire       opll_a0;
    wire       opll_cs_n;
    wire       opll_wr_n;
    wire [2:0] detect_reg;
    wire       fm_enable;

    assign mem_d = bus_data_oe ? bus_data_out : 8'hZZ;

    sms_fm_bus u_bus (
        .clk                (clk_14m318),
        .reset_n            (reset_n),
        .core_ready         (fm_core_ready),
        .sms_mode           (sms_mode),
        .usb_mode           (usb_mode),
        .sms_a              (cart_a),
        .sms_data_in        (mem_d),
        .sms_iorq_n         (cart_a18_iorq_n),
        .sms_wr_n           (lwr_n),
        .sms_rd_n           (cas0_n),
        .sms_data_out       (bus_data_out),
        .sms_data_oe        (bus_data_oe),
        .opll_data          (opll_data),
        .opll_a0            (opll_a0),
        .opll_cs_n          (opll_cs_n),
        .opll_wr_n          (opll_wr_n),
        .detect_reg         (detect_reg),
        .fm_enable          (fm_enable)
    );

    wire opll_acc_strobe;
    wire signed [15:0] opll_acc_sample;
    wire [1:0] unused_dout;
    wire unused_dout_oe;
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
    ) u_opll (
        .i_XIN_EMUCLK         (clk_14m318),
        .o_XOUT               (unused_xout),
        .i_phiM_PCEN_n        (phim_pcen_n),
        .i_IC_n               (core_reset_n),
        .i_ALTPATCH_EN        (1'b0),
        .i_CS_n               (opll_cs_n),
        .i_WR_n               (opll_wr_n),
        .i_A0                 (opll_a0),
        .i_D                  (opll_data),
        .o_D                  (unused_dout),
        .o_D_OE               (unused_dout_oe),
        .o_DAC_EN_MO          (unused_dac_mo),
        .o_DAC_EN_RO          (unused_dac_ro),
        .o_IMP_NOFLUC_SIGN    (unused_imp_sign),
        .o_IMP_NOFLUC_MAG     (unused_imp_mag),
        .o_IMP_FLUC_SIGNED_MO (unused_imp_mo),
        .o_IMP_FLUC_SIGNED_RO (unused_imp_ro),
        .i_ACC_SIGNED_MOVOL   (5'sd2),
        .i_ACC_SIGNED_ROVOL   (5'sd3),
        .o_ACC_SIGNED_STRB    (opll_acc_strobe),
        .o_ACC_SIGNED         (opll_acc_sample)
    );

    reg strobe_q;
    reg signed [15:0] audio_sample;
    initial begin
        strobe_q = 1'b0;
        audio_sample = 16'sd0;
    end
    always @(posedge clk_14m318 or negedge core_reset_n) begin
        if (!core_reset_n) begin
            strobe_q <= 1'b0;
            audio_sample <= 16'sd0;
        end else begin
            strobe_q <= opll_acc_strobe;
            if (!sms_mode || usb_mode || !fm_enable)
                audio_sample <= 16'sd0;
            else if (opll_acc_strobe && !strobe_q)
                audio_sample <= opll_acc_sample;
        end
    end

    pdm_dac u_pdm (
        .clk       (clk_14m318),
        .reset_n   (core_reset_n),
        .sample    (audio_sample),
        .pdm_out   (fm_pdm)
    );

    assign fm_active = fm_core_ready && sms_mode && !usb_mode && fm_enable;

endmodule
