// Top-level module: RGB Depthwise + Pointwise Convolution Pipeline
// Wires line buffers -> 3x3 depthwise convs -> 1x1 pointwise -> AXI-Stream output

module axi4s_rgb_dw_pw_top #(
    parameter IMAGE_WIDTH = 640,
    parameter IMAGE_HEIGHT = 480,
    parameter DATA_WIDTH = 24,  // RGB 8-bit per channel
    parameter CONV_DATA_WIDTH = 16,
    parameter OUTPUT_WIDTH = 8
)(
    // Clock and reset
    input  wire                     clk,
    input  wire                     rst_n,
    
    // AXI4-Lite control interface
    input  wire                     s_axi_aclk,
    input  wire                     s_axi_aresetn,
    input  wire [7:0]               s_axi_awaddr,
    input  wire [2:0]               s_axi_awprot,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [31:0]              s_axi_wdata,
    input  wire [3:0]               s_axi_wstrb,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output wire [1:0]               s_axi_bresp,
    output wire                     s_axi_bvalid,
    input  wire                     s_axi_bready,
    input  wire [7:0]               s_axi_araddr,
    input  wire [2:0]               s_axi_arprot,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output wire [31:0]              s_axi_rdata,
    output wire [1:0]               s_axi_rresp,
    output wire                     s_axi_rvalid,
    input  wire                     s_axi_rready,
    
    // AXI4-Stream input (RGB)
    input  wire [DATA_WIDTH-1:0]    s_axis_tdata,
    input  wire                     s_axis_tvalid,
    output wire                     s_axis_tready,
    input  wire                     s_axis_tlast,
    input  wire [2:0]               s_axis_tuser,
    
    // AXI4-Stream output (processed RGB)
    output wire [DATA_WIDTH-1:0]    m_axis_tdata,
    output wire                     m_axis_tvalid,
    input  wire                     m_axis_tready,
    output wire                     m_axis_tlast,
    output wire [2:0]               m_axis_tuser
);

    // Internal signals
    wire [DATA_WIDTH-1:0] rgb_data;
    wire [2:0] r_data, g_data, b_data;
    wire [2:0] r_valid, g_valid, b_valid;
    wire [2:0] r_ready, g_ready, b_ready;
    wire [2:0] r_last, g_last, b_last;
    wire [2:0] r_user, g_user, b_user;
    
    // Line buffer outputs (3x3 windows)
    wire [DATA_WIDTH*9-1:0] r_window, g_window, b_window;
    wire [2:0] window_valid, window_ready;
    wire [2:0] window_last, window_user;
    
    // Depthwise convolution outputs
    wire [CONV_DATA_WIDTH*3-1:0] dw_out_data;
    wire [2:0] dw_out_valid, dw_out_ready;
    wire [2:0] dw_out_last, dw_out_user;
    
    // Pointwise convolution output
    wire [OUTPUT_WIDTH*3-1:0] pw_out_data;
    wire pw_out_valid, pw_out_ready;
    wire pw_out_last;
    wire [2:0] pw_out_user;
    
    // Control signals from AXI4-Lite
    wire [7:0] kernel_00, kernel_01, kernel_02;
    wire [7:0] kernel_10, kernel_11, kernel_12;
    wire [7:0] kernel_20, kernel_21, kernel_22;
    wire [7:0] relu_threshold;
    wire [1:0] stride;
    wire enable_relu;
    wire enable_processing;
    
    wire [7:0] pw_weights [0:8];
    wire [15:0] pw_biases [0:2];
    
    // RGB channel separation
    assign r_data = s_axis_tdata[7:0];
    assign g_data = s_axis_tdata[15:8];
    assign b_data = s_axis_tdata[23:16];
    
    assign rgb_data = {b_data, g_data, r_data};  // Pack back to RGB
    
    // AXI4-Lite register interface
    axi4l_regs_ext #(
        .C_S_AXI_DATA_WIDTH(32),
        .C_S_AXI_ADDR_WIDTH(8)
    ) regs_inst (
        .S_AXI_ACLK(s_axi_aclk),
        .S_AXI_ARESETN(s_axi_aresetn),
        .S_AXI_AWADDR(s_axi_awaddr),
        .S_AXI_AWPROT(s_axi_awprot),
        .S_AXI_AWVALID(s_axi_awvalid),
        .S_AXI_AWREADY(s_axi_awready),
        .S_AXI_WDATA(s_axi_wdata),
        .S_AXI_WSTRB(s_axi_wstrb),
        .S_AXI_WVALID(s_axi_wvalid),
        .S_AXI_WREADY(s_axi_wready),
        .S_AXI_BRESP(s_axi_bresp),
        .S_AXI_BVALID(s_axi_bvalid),
        .S_AXI_BREADY(s_axi_bready),
        .S_AXI_ARADDR(s_axi_araddr),
        .S_AXI_ARPROT(s_axi_arprot),
        .S_AXI_ARVALID(s_axi_arvalid),
        .S_AXI_ARREADY(s_axi_arready),
        .S_AXI_RDATA(s_axi_rdata),
        .S_AXI_RRESP(s_axi_rresp),
        .S_AXI_RVALID(s_axi_rvalid),
        .S_AXI_RREADY(s_axi_rready),
        
        // Control outputs
        .kernel_00(kernel_00), .kernel_01(kernel_01), .kernel_02(kernel_02),
        .kernel_10(kernel_10), .kernel_11(kernel_11), .kernel_12(kernel_12),
        .kernel_20(kernel_20), .kernel_21(kernel_21), .kernel_22(kernel_22),
        .relu_threshold(relu_threshold),
        .stride(stride),
        .enable_relu(enable_relu),
        .enable_processing(enable_processing),
        .pw_weights(pw_weights),
        .pw_biases(pw_biases),
        
        // Performance counters
        .perf_clk(clk),
        .perf_rst_n(rst_n),
        .tvalid_in(s_axis_tvalid),
        .tready_in(s_axis_tready),
        .tvalid_out(m_axis_tvalid),
        .tready_out(m_axis_tready)
    );
    
    // Line buffers for each RGB channel
    linebuf_3_rv #(
        .WIDTH(IMAGE_WIDTH),
        .HEIGHT(IMAGE_HEIGHT),
        .DATA_WIDTH(8)
    ) linebuf_r (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_tdata(r_data),
        .s_axis_tvalid(r_valid),
        .s_axis_tready(r_ready),
        .s_axis_tlast(r_last),
        .s_axis_tuser(r_user),
        .m_axis_tdata(r_window),
        .m_axis_tvalid(window_valid[0]),
        .m_axis_tready(window_ready[0]),
        .m_axis_tlast(window_last[0]),
        .m_axis_tuser(window_user[0])
    );
    
    linebuf_3_rv #(
        .WIDTH(IMAGE_WIDTH),
        .HEIGHT(IMAGE_HEIGHT),
        .DATA_WIDTH(8)
    ) linebuf_g (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_tdata(g_data),
        .s_axis_tvalid(g_valid),
        .s_axis_tready(g_ready),
        .s_axis_tlast(g_last),
        .s_axis_tuser(g_user),
        .m_axis_tdata(g_window),
        .m_axis_tvalid(window_valid[1]),
        .m_axis_tready(window_ready[1]),
        .m_axis_tlast(window_last[1]),
        .m_axis_tuser(window_user[1])
    );
    
    linebuf_3_rv #(
        .WIDTH(IMAGE_WIDTH),
        .HEIGHT(IMAGE_HEIGHT),
        .DATA_WIDTH(8)
    ) linebuf_b (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_tdata(b_data),
        .s_axis_tvalid(b_valid),
        .s_axis_tready(b_ready),
        .s_axis_tlast(b_last),
        .s_axis_tuser(b_user),
        .m_axis_tdata(b_window),
        .m_axis_tvalid(window_valid[2]),
        .m_axis_tready(window_ready[2]),
        .m_axis_tlast(window_last[2]),
        .m_axis_tuser(window_user[2])
    );
    
    // Depthwise 3x3 convolutions for each channel
    conv3x3_int8_rv #(
        .DATA_WIDTH(8),
        .KERNEL_WIDTH(8),
        .OUTPUT_WIDTH(CONV_DATA_WIDTH)
    ) conv_r (
        .clk(clk),
        .rst_n(rst_n),
        .kernel_00(kernel_00), .kernel_01(kernel_01), .kernel_02(kernel_02),
        .kernel_10(kernel_10), .kernel_11(kernel_11), .kernel_12(kernel_12),
        .kernel_20(kernel_20), .kernel_21(kernel_21), .kernel_22(kernel_22),
        .relu_threshold(relu_threshold),
        .stride(stride),
        .enable_relu(enable_relu),
        .s_axis_tdata(r_window),
        .s_axis_tvalid(window_valid[0]),
        .s_axis_tready(window_ready[0]),
        .s_axis_tlast(window_last[0]),
        .s_axis_tuser(window_user[0]),
        .m_axis_tdata(dw_out_data[CONV_DATA_WIDTH*1-1:CONV_DATA_WIDTH*0]),
        .m_axis_tvalid(dw_out_valid[0]),
        .m_axis_tready(dw_out_ready[0]),
        .m_axis_tlast(dw_out_last[0]),
        .m_axis_tuser(dw_out_user[0])
    );
    
    conv3x3_int8_rv #(
        .DATA_WIDTH(8),
        .KERNEL_WIDTH(8),
        .OUTPUT_WIDTH(CONV_DATA_WIDTH)
    ) conv_g (
        .clk(clk),
        .rst_n(rst_n),
        .kernel_00(kernel_00), .kernel_01(kernel_01), .kernel_02(kernel_02),
        .kernel_10(kernel_10), .kernel_11(kernel_11), .kernel_12(kernel_12),
        .kernel_20(kernel_20), .kernel_21(kernel_21), .kernel_22(kernel_22),
        .relu_threshold(relu_threshold),
        .stride(stride),
        .enable_relu(enable_relu),
        .s_axis_tdata(g_window),
        .s_axis_tvalid(window_valid[1]),
        .s_axis_tready(window_ready[1]),
        .s_axis_tlast(window_last[1]),
        .s_axis_tuser(window_user[1]),
        .m_axis_tdata(dw_out_data[CONV_DATA_WIDTH*2-1:CONV_DATA_WIDTH*1]),
        .m_axis_tvalid(dw_out_valid[1]),
        .m_axis_tready(dw_out_ready[1]),
        .m_axis_tlast(dw_out_last[1]),
        .m_axis_tuser(dw_out_user[1])
    );
    
    conv3x3_int8_rv #(
        .DATA_WIDTH(8),
        .KERNEL_WIDTH(8),
        .OUTPUT_WIDTH(CONV_DATA_WIDTH)
    ) conv_b (
        .clk(clk),
        .rst_n(rst_n),
        .kernel_00(kernel_00), .kernel_01(kernel_01), .kernel_02(kernel_02),
        .kernel_10(kernel_10), .kernel_11(kernel_11), .kernel_12(kernel_12),
        .kernel_20(kernel_20), .kernel_21(kernel_21), .kernel_22(kernel_22),
        .relu_threshold(relu_threshold),
        .stride(stride),
        .enable_relu(enable_relu),
        .s_axis_tdata(b_window),
        .s_axis_tvalid(window_valid[2]),
        .s_axis_tready(window_ready[2]),
        .s_axis_tlast(window_last[2]),
        .s_axis_tuser(window_user[2]),
        .m_axis_tdata(dw_out_data[CONV_DATA_WIDTH*3-1:CONV_DATA_WIDTH*2]),
        .m_axis_tvalid(dw_out_valid[2]),
        .m_axis_tready(dw_out_ready[2]),
        .m_axis_tlast(dw_out_last[2]),
        .m_axis_tuser(dw_out_user[2])
    );
    
    // Pointwise 1x1 convolution for channel mixing
    conv1x1_pointwise #(
        .INPUT_CHANNELS(3),
        .OUTPUT_CHANNELS(3),
        .DATA_WIDTH(CONV_DATA_WIDTH),
        .WEIGHT_WIDTH(8),
        .BIAS_WIDTH(16),
        .OUTPUT_DATA_WIDTH(OUTPUT_WIDTH)
    ) pointwise_inst (
        .clk(clk),
        .rst_n(rst_n),
        .weights(pw_weights),
        .biases(pw_biases),
        .s_axis_tdata(dw_out_data),
        .s_axis_tvalid(&dw_out_valid),  // All channels must be valid
        .s_axis_tready(&dw_out_ready),  // All channels must be ready
        .s_axis_tlast(dw_out_last[0]),
        .s_axis_tuser(dw_out_user[0]),
        .m_axis_tdata(pw_out_data),
        .m_axis_tvalid(pw_out_valid),
        .m_axis_tready(pw_out_ready),
        .m_axis_tlast(pw_out_last),
        .m_axis_tuser(pw_out_user)
    );
    
    // Channel routing
    assign r_valid = s_axis_tvalid;
    assign g_valid = s_axis_tvalid;
    assign b_valid = s_axis_tvalid;
    assign r_last = s_axis_tlast;
    assign g_last = s_axis_tlast;
    assign b_last = s_axis_tlast;
    assign r_user = s_axis_tuser;
    assign g_user = s_axis_tuser;
    assign b_user = s_axis_tuser;
    
    // Output assignment
    assign s_axis_tready = r_ready && g_ready && b_ready;
    assign dw_out_ready[0] = pw_out_ready;
    assign dw_out_ready[1] = pw_out_ready;
    assign dw_out_ready[2] = pw_out_ready;
    assign pw_out_ready = m_axis_tready;
    
    assign m_axis_tdata = pw_out_data;
    assign m_axis_tvalid = pw_out_valid;
    assign m_axis_tlast = pw_out_last;
    assign m_axis_tuser = pw_out_user;

endmodule

