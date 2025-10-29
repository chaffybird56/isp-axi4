// Depthwise 3x3 INT8 Convolution with ready/valid interface
// Implements separable convolution depthwise stage

module conv3x3_int8_rv #(
    parameter DATA_WIDTH = 8,
    parameter KERNEL_WIDTH = 8,
    parameter OUTPUT_WIDTH = 16  // Accumulator width
)(
    input  wire                     clk,
    input  wire                     rst_n,
    
    // Control interface
    input  wire [7:0]               kernel_00, kernel_01, kernel_02,
    input  wire [7:0]               kernel_10, kernel_11, kernel_12,
    input  wire [7:0]               kernel_20, kernel_21, kernel_22,
    input  wire [7:0]               relu_threshold,
    input  wire [1:0]               stride,
    input  wire                     enable_relu,
    
    // AXI4-Stream input - 3x3 window
    input  wire [DATA_WIDTH*9-1:0]  s_axis_tdata,
    input  wire                     s_axis_tvalid,
    output reg                      s_axis_tready,
    input  wire                     s_axis_tlast,
    input  wire [2:0]               s_axis_tuser,
    
    // AXI4-Stream output
    output reg  [OUTPUT_WIDTH-1:0]  m_axis_tdata,
    output reg                      m_axis_tvalid,
    input  wire                     m_axis_tready,
    output reg                      m_axis_tlast,
    output reg  [2:0]               m_axis_tuser
);

    // Internal signals
    reg [DATA_WIDTH-1:0] pixel_window [0:8];
    reg [KERNEL_WIDTH-1:0] kernel [0:8];
    reg [OUTPUT_WIDTH-1:0] accumulator;
    reg [2:0] state;
    
    localparam IDLE = 3'd0;
    localparam LOAD_WINDOW = 3'd1;
    localparam COMPUTE = 3'd2;
    localparam OUTPUT = 3'd3;
    
    // MAC units
    wire [OUTPUT_WIDTH-1:0] mac_results [0:8];
    reg [OUTPUT_WIDTH-1:0] sum_result;
    
    // Generate MAC units for each pixel
    genvar i;
    generate
        for (i = 0; i < 9; i = i + 1) begin : mac_gen
            assign mac_results[i] = $signed(pixel_window[i]) * $signed(kernel[i]);
        end
    endgenerate
    
    // Main state machine
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axis_tready <= 1'b1;
            m_axis_tvalid <= 1'b0;
            m_axis_tlast <= 1'b0;
            m_axis_tuser <= 3'd0;
            m_axis_tdata <= {OUTPUT_WIDTH{1'b0}};
            
            state <= IDLE;
            accumulator <= {OUTPUT_WIDTH{1'b0}};
            sum_result <= {OUTPUT_WIDTH{1'b0}};
        end else begin
            case (state)
                IDLE: begin
                    s_axis_tready <= 1'b1;
                    m_axis_tvalid <= 1'b0;
                    
                    if (s_axis_tvalid && s_axis_tready) begin
                        state <= LOAD_WINDOW;
                    end
                end
                
                LOAD_WINDOW: begin
                    s_axis_tready <= 1'b0;
                    
                    // Load pixel window from input
                    pixel_window[0] <= s_axis_tdata[DATA_WIDTH*1-1:DATA_WIDTH*0];
                    pixel_window[1] <= s_axis_tdata[DATA_WIDTH*2-1:DATA_WIDTH*1];
                    pixel_window[2] <= s_axis_tdata[DATA_WIDTH*3-1:DATA_WIDTH*2];
                    pixel_window[3] <= s_axis_tdata[DATA_WIDTH*4-1:DATA_WIDTH*3];
                    pixel_window[4] <= s_axis_tdata[DATA_WIDTH*5-1:DATA_WIDTH*4];
                    pixel_window[5] <= s_axis_tdata[DATA_WIDTH*6-1:DATA_WIDTH*5];
                    pixel_window[6] <= s_axis_tdata[DATA_WIDTH*7-1:DATA_WIDTH*6];
                    pixel_window[7] <= s_axis_tdata[DATA_WIDTH*8-1:DATA_WIDTH*7];
                    pixel_window[8] <= s_axis_tdata[DATA_WIDTH*9-1:DATA_WIDTH*8];
                    
                    // Load kernel
                    kernel[0] <= kernel_00;
                    kernel[1] <= kernel_01;
                    kernel[2] <= kernel_02;
                    kernel[3] <= kernel_10;
                    kernel[4] <= kernel_11;
                    kernel[5] <= kernel_12;
                    kernel[6] <= kernel_20;
                    kernel[7] <= kernel_21;
                    kernel[8] <= kernel_22;
                    
                    // Store control signals
                    m_axis_tlast <= s_axis_tlast;
                    m_axis_tuser <= s_axis_tuser;
                    
                    state <= COMPUTE;
                end
                
                COMPUTE: begin
                    // Sum all MAC results
                    sum_result <= mac_results[0] + mac_results[1] + mac_results[2] +
                                 mac_results[3] + mac_results[4] + mac_results[5] +
                                 mac_results[6] + mac_results[7] + mac_results[8];
                    
                    state <= OUTPUT;
                end
                
                OUTPUT: begin
                    // Apply ReLU if enabled
                    if (enable_relu && $signed(sum_result) < $signed(relu_threshold)) begin
                        m_axis_tdata <= relu_threshold;
                    end else begin
                        m_axis_tdata <= sum_result;
                    end
                    
                    m_axis_tvalid <= 1'b1;
                    
                    // Wait for handshake
                    if (m_axis_tvalid && m_axis_tready) begin
                        m_axis_tvalid <= 1'b0;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end

endmodule

