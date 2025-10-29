// AXI4-Lite Register Interface with Performance Counters
// Provides control registers and read-only performance counters

module axi4l_regs_ext #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 8
)(
    // AXI4-Lite interface
    input  wire                           S_AXI_ACLK,
    input  wire                           S_AXI_ARESETN,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]  S_AXI_AWADDR,
    input  wire [2:0]                     S_AXI_AWPROT,
    input  wire                           S_AXI_AWVALID,
    output reg                            S_AXI_AWREADY,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]  S_AXI_WDATA,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] S_AXI_WSTRB,
    input  wire                           S_AXI_WVALID,
    output reg                            S_AXI_WREADY,
    output reg  [1:0]                     S_AXI_BRESP,
    output reg                            S_AXI_BVALID,
    input  wire                           S_AXI_BREADY,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]  S_AXI_ARADDR,
    input  wire [2:0]                     S_AXI_ARPROT,
    input  wire                           S_AXI_ARVALID,
    output reg                            S_AXI_ARREADY,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]  S_AXI_RDATA,
    output reg  [1:0]                     S_AXI_RRESP,
    output reg                            S_AXI_RVALID,
    input  wire                           S_AXI_RREADY,
    
    // Control outputs
    output reg  [7:0]                     kernel_00, kernel_01, kernel_02,
    output reg  [7:0]                     kernel_10, kernel_11, kernel_12,
    output reg  [7:0]                     kernel_20, kernel_21, kernel_22,
    output reg  [7:0]                     relu_threshold,
    output reg  [1:0]                     stride,
    output reg                            enable_relu,
    output reg                            enable_processing,
    
    // Pointwise weights (3x3 matrix)
    output reg  [7:0]                     pw_weights [0:8],  // 3x3 weight matrix
    output reg  [15:0]                    pw_biases [0:2],  // 3 bias values
    
    // Performance counter inputs
    input  wire                           perf_clk,
    input  wire                           perf_rst_n,
    input  wire                           tvalid_in,
    input  wire                           tready_in,
    input  wire                           tvalid_out,
    input  wire                           tready_out
);

    // Register map
    localparam REG_KERNEL_00     = 8'h00;
    localparam REG_KERNEL_01     = 8'h04;
    localparam REG_KERNEL_02     = 8'h08;
    localparam REG_KERNEL_10     = 8'h0C;
    localparam REG_KERNEL_11     = 8'h10;
    localparam REG_KERNEL_12     = 8'h14;
    localparam REG_KERNEL_20     = 8'h18;
    localparam REG_KERNEL_21     = 8'h1C;
    localparam REG_KERNEL_22     = 8'h20;
    localparam REG_RELU_THRESH   = 8'h24;
    localparam REG_STRIDE        = 8'h28;
    localparam REG_CONTROL       = 8'h2C;
    
    // Pointwise weights (0x30-0x50)
    localparam REG_PW_WEIGHT_00  = 8'h30;
    localparam REG_PW_WEIGHT_01  = 8'h34;
    localparam REG_PW_WEIGHT_02  = 8'h38;
    localparam REG_PW_WEIGHT_10  = 8'h3C;
    localparam REG_PW_WEIGHT_11  = 8'h40;
    localparam REG_PW_WEIGHT_12  = 8'h44;
    localparam REG_PW_WEIGHT_20  = 8'h48;
    localparam REG_PW_WEIGHT_21  = 8'h4C;
    localparam REG_PW_WEIGHT_22  = 8'h50;
    localparam REG_PW_BIAS_0     = 8'h54;
    localparam REG_PW_BIAS_1     = 8'h58;
    localparam REG_PW_BIAS_2     = 8'h5C;
    
    // Performance counters (read-only)
    localparam REG_CYCLES        = 8'h60;
    localparam REG_PIXELS_IN     = 8'h64;
    localparam REG_PIXELS_OUT    = 8'h68;
    localparam REG_STALL_CYCLES  = 8'h6C;
    
    // Internal signals
    reg [C_S_AXI_DATA_WIDTH-1:0] reg_data_out;
    reg                           aw_en;
    
    // Performance counters
    reg [31:0] cycle_count;
    reg [31:0] pixels_in_count;
    reg [31:0] pixels_out_count;
    reg [31:0] stall_count;
    
    // AXI write address channel
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_AWREADY <= 1'b0;
            aw_en <= 1'b1;
        end else begin
            if (~S_AXI_AWREADY && S_AXI_AWVALID && S_AXI_WVALID && aw_en) begin
                S_AXI_AWREADY <= 1'b1;
                aw_en <= 1'b0;
            end else if (S_AXI_BREADY && S_AXI_BVALID) begin
                aw_en <= 1'b1;
                S_AXI_AWREADY <= 1'b0;
            end else begin
                S_AXI_AWREADY <= 1'b0;
            end
        end
    end
    
    // AXI write data channel
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_WREADY <= 1'b0;
        end else begin
            if (~S_AXI_WREADY && S_AXI_WVALID && S_AXI_AWVALID && aw_en) begin
                S_AXI_WREADY <= 1'b1;
            end else begin
                S_AXI_WREADY <= 1'b0;
            end
        end
    end
    
    // AXI write response channel
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_BVALID <= 1'b0;
            S_AXI_BRESP <= 2'b0;
        end else begin
            if (S_AXI_AWREADY && S_AXI_AWVALID && ~S_AXI_BVALID && S_AXI_WREADY && S_AXI_WVALID) begin
                S_AXI_BVALID <= 1'b1;
                S_AXI_BRESP <= 2'b0; // OKAY response
            end else if (S_AXI_BREADY && S_AXI_BVALID) begin
                S_AXI_BVALID <= 1'b0;
            end
        end
    end
    
    // Register write logic
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            kernel_00 <= 8'h00;
            kernel_01 <= 8'h00;
            kernel_02 <= 8'h00;
            kernel_10 <= 8'h00;
            kernel_11 <= 8'h01;  // Identity kernel
            kernel_12 <= 8'h00;
            kernel_20 <= 8'h00;
            kernel_21 <= 8'h00;
            kernel_22 <= 8'h00;
            relu_threshold <= 8'h00;
            stride <= 2'b01;     // Stride 1
            enable_relu <= 1'b0;
            enable_processing <= 1'b1;
            
            // Initialize pointwise weights to identity
            pw_weights[0] <= 8'h01; pw_weights[1] <= 8'h00; pw_weights[2] <= 8'h00;
            pw_weights[3] <= 8'h00; pw_weights[4] <= 8'h01; pw_weights[5] <= 8'h00;
            pw_weights[6] <= 8'h00; pw_weights[7] <= 8'h00; pw_weights[8] <= 8'h01;
            pw_biases[0] <= 16'h0000;
            pw_biases[1] <= 16'h0000;
            pw_biases[2] <= 16'h0000;
        end else begin
            if (S_AXI_WREADY && S_AXI_WVALID && S_AXI_AWREADY && S_AXI_AWVALID) begin
                case (S_AXI_AWADDR[7:0])
                    REG_KERNEL_00:     kernel_00 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_01:     kernel_01 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_02:     kernel_02 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_10:     kernel_10 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_11:     kernel_11 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_12:     kernel_12 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_20:     kernel_20 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_21:     kernel_21 <= S_AXI_WDATA[7:0];
                    REG_KERNEL_22:     kernel_22 <= S_AXI_WDATA[7:0];
                    REG_RELU_THRESH:   relu_threshold <= S_AXI_WDATA[7:0];
                    REG_STRIDE:        stride <= S_AXI_WDATA[1:0];
                    REG_CONTROL:       begin
                        enable_relu <= S_AXI_WDATA[0];
                        enable_processing <= S_AXI_WDATA[1];
                    end
                    
                    REG_PW_WEIGHT_00:  pw_weights[0] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_01:  pw_weights[1] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_02:  pw_weights[2] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_10:  pw_weights[3] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_11:  pw_weights[4] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_12:  pw_weights[5] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_20:  pw_weights[6] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_21:  pw_weights[7] <= S_AXI_WDATA[7:0];
                    REG_PW_WEIGHT_22:  pw_weights[8] <= S_AXI_WDATA[7:0];
                    REG_PW_BIAS_0:     pw_biases[0] <= S_AXI_WDATA[15:0];
                    REG_PW_BIAS_1:     pw_biases[1] <= S_AXI_WDATA[15:0];
                    REG_PW_BIAS_2:     pw_biases[2] <= S_AXI_WDATA[15:0];
                endcase
            end
        end
    end
    
    // AXI read address channel
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_ARREADY <= 1'b0;
        end else begin
            if (~S_AXI_ARREADY && S_AXI_ARVALID) begin
                S_AXI_ARREADY <= 1'b1;
            end else begin
                S_AXI_ARREADY <= 1'b0;
            end
        end
    end
    
    // Register read logic
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_RVALID <= 1'b0;
            S_AXI_RRESP <= 2'b0;
        end else begin
            if (S_AXI_ARREADY && S_AXI_ARVALID && ~S_AXI_RVALID) begin
                S_AXI_RVALID <= 1'b1;
                S_AXI_RRESP <= 2'b0; // OKAY response
                
                case (S_AXI_ARADDR[7:0])
                    REG_KERNEL_00:     reg_data_out <= {24'h000000, kernel_00};
                    REG_KERNEL_01:     reg_data_out <= {24'h000000, kernel_01};
                    REG_KERNEL_02:     reg_data_out <= {24'h000000, kernel_02};
                    REG_KERNEL_10:     reg_data_out <= {24'h000000, kernel_10};
                    REG_KERNEL_11:     reg_data_out <= {24'h000000, kernel_11};
                    REG_KERNEL_12:     reg_data_out <= {24'h000000, kernel_12};
                    REG_KERNEL_20:     reg_data_out <= {24'h000000, kernel_20};
                    REG_KERNEL_21:     reg_data_out <= {24'h000000, kernel_21};
                    REG_KERNEL_22:     reg_data_out <= {24'h000000, kernel_22};
                    REG_RELU_THRESH:   reg_data_out <= {24'h000000, relu_threshold};
                    REG_STRIDE:        reg_data_out <= {30'h00000000, stride};
                    REG_CONTROL:       reg_data_out <= {30'h00000000, enable_processing, enable_relu};
                    
                    REG_PW_WEIGHT_00:  reg_data_out <= {24'h000000, pw_weights[0]};
                    REG_PW_WEIGHT_01:  reg_data_out <= {24'h000000, pw_weights[1]};
                    REG_PW_WEIGHT_02:  reg_data_out <= {24'h000000, pw_weights[2]};
                    REG_PW_WEIGHT_10:  reg_data_out <= {24'h000000, pw_weights[3]};
                    REG_PW_WEIGHT_11:  reg_data_out <= {24'h000000, pw_weights[4]};
                    REG_PW_WEIGHT_12:  reg_data_out <= {24'h000000, pw_weights[5]};
                    REG_PW_WEIGHT_20:  reg_data_out <= {24'h000000, pw_weights[6]};
                    REG_PW_WEIGHT_21:  reg_data_out <= {24'h000000, pw_weights[7]};
                    REG_PW_WEIGHT_22:  reg_data_out <= {24'h000000, pw_weights[8]};
                    REG_PW_BIAS_0:     reg_data_out <= {16'h0000, pw_biases[0]};
                    REG_PW_BIAS_1:     reg_data_out <= {16'h0000, pw_biases[1]};
                    REG_PW_BIAS_2:     reg_data_out <= {16'h0000, pw_biases[2]};
                    
                    // Performance counters (read-only)
                    REG_CYCLES:        reg_data_out <= cycle_count;
                    REG_PIXELS_IN:     reg_data_out <= pixels_in_count;
                    REG_PIXELS_OUT:    reg_data_out <= pixels_out_count;
                    REG_STALL_CYCLES:  reg_data_out <= stall_count;
                    
                    default:           reg_data_out <= 32'h00000000;
                endcase
            end else if (S_AXI_RVALID && S_AXI_RREADY) begin
                S_AXI_RVALID <= 1'b0;
            end
        end
    end
    
    // Performance counters
    always @(posedge perf_clk or negedge perf_rst_n) begin
        if (!perf_rst_n) begin
            cycle_count <= 32'h0;
            pixels_in_count <= 32'h0;
            pixels_out_count <= 32'h0;
            stall_count <= 32'h0;
        end else begin
            // Cycle counter
            cycle_count <= cycle_count + 1'b1;
            
            // Pixel input counter
            if (tvalid_in && tready_in) begin
                pixels_in_count <= pixels_in_count + 1'b1;
            end
            
            // Pixel output counter
            if (tvalid_out && tready_out) begin
                pixels_out_count <= pixels_out_count + 1'b1;
            end
            
            // Stall counter (valid but not ready)
            if (tvalid_in && !tready_in) begin
                stall_count <= stall_count + 1'b1;
            end
        end
    end

endmodule

