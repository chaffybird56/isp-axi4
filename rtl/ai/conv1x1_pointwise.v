// Pointwise 1x1 Convolution for channel mixing
// Mixes 3 input channels (RGB) into 3 output channels

module conv1x1_pointwise #(
    parameter INPUT_CHANNELS = 3,
    parameter OUTPUT_CHANNELS = 3,
    parameter DATA_WIDTH = 16,  // Input data width
    parameter WEIGHT_WIDTH = 8,
    parameter BIAS_WIDTH = 16,
    parameter OUTPUT_DATA_WIDTH = 8
)(
    input  wire                     clk,
    input  wire                     rst_n,
    
    // Weight and bias configuration
    input  wire [WEIGHT_WIDTH-1:0]  weights [0:INPUT_CHANNELS*OUTPUT_CHANNELS-1],
    input  wire [BIAS_WIDTH-1:0]    biases [0:OUTPUT_CHANNELS-1],
    
    // AXI4-Stream input - 3 channels
    input  wire [DATA_WIDTH*INPUT_CHANNELS-1:0] s_axis_tdata,
    input  wire                     s_axis_tvalid,
    output reg                      s_axis_tready,
    input  wire                     s_axis_tlast,
    input  wire [2:0]               s_axis_tuser,
    
    // AXI4-Stream output - 3 channels
    output reg  [OUTPUT_DATA_WIDTH*OUTPUT_CHANNELS-1:0] m_axis_tdata,
    output reg                      m_axis_tvalid,
    input  wire                     m_axis_tready,
    output reg                      m_axis_tlast,
    output reg  [2:0]               m_axis_tuser
);

    // Internal signals
    reg [DATA_WIDTH-1:0] input_channels [0:INPUT_CHANNELS-1];
    reg [OUTPUT_DATA_WIDTH-1:0] output_channels [0:OUTPUT_CHANNELS-1];
    
    // MAC results for each output channel
    wire [DATA_WIDTH+WEIGHT_WIDTH-1:0] mac_results [0:OUTPUT_CHANNELS-1];
    reg [DATA_WIDTH+WEIGHT_WIDTH-1:0] temp_results [0:OUTPUT_CHANNELS-1];
    
    // State machine
    reg [1:0] state;
    localparam IDLE = 2'd0;
    localparam COMPUTE = 2'd1;
    localparam OUTPUT = 2'd2;
    
    // Generate MAC units for each output channel
    genvar out_ch, in_ch;
    generate
        for (out_ch = 0; out_ch < OUTPUT_CHANNELS; out_ch = out_ch + 1) begin : output_channel
            reg [DATA_WIDTH+WEIGHT_WIDTH-1:0] channel_sum;
            
            always @(*) begin
                channel_sum = $signed(biases[out_ch]);
                for (in_ch = 0; in_ch < INPUT_CHANNELS; in_ch = in_ch + 1) begin
                    channel_sum = channel_sum + ($signed(input_channels[in_ch]) * 
                                                $signed(weights[out_ch * INPUT_CHANNELS + in_ch]));
                end
            end
            
            assign mac_results[out_ch] = channel_sum;
        end
    endgenerate
    
    // Main processing
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axis_tready <= 1'b1;
            m_axis_tvalid <= 1'b0;
            m_axis_tlast <= 1'b0;
            m_axis_tuser <= 3'd0;
            m_axis_tdata <= {OUTPUT_DATA_WIDTH*OUTPUT_CHANNELS{1'b0}};
            
            state <= IDLE;
        end else begin
            case (state)
                IDLE: begin
                    s_axis_tready <= 1'b1;
                    m_axis_tvalid <= 1'b0;
                    
                    if (s_axis_tvalid && s_axis_tready) begin
                        // Load input channels
                        input_channels[0] <= s_axis_tdata[DATA_WIDTH*1-1:DATA_WIDTH*0];
                        input_channels[1] <= s_axis_tdata[DATA_WIDTH*2-1:DATA_WIDTH*1];
                        input_channels[2] <= s_axis_tdata[DATA_WIDTH*3-1:DATA_WIDTH*2];
                        
                        // Store control signals
                        m_axis_tlast <= s_axis_tlast;
                        m_axis_tuser <= s_axis_tuser;
                        
                        s_axis_tready <= 1'b0;
                        state <= COMPUTE;
                    end
                end
                
                COMPUTE: begin
                    // Compute each output channel
                    output_channels[0] <= mac_results[0][OUTPUT_DATA_WIDTH-1:0];
                    output_channels[1] <= mac_results[1][OUTPUT_DATA_WIDTH-1:0];
                    output_channels[2] <= mac_results[2][OUTPUT_DATA_WIDTH-1:0];
                    
                    state <= OUTPUT;
                end
                
                OUTPUT: begin
                    // Pack output channels
                    m_axis_tdata <= {output_channels[2], output_channels[1], output_channels[0]};
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

