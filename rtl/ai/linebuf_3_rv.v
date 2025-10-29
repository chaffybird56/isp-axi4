// Line buffer with 3-line window and ready/valid interface
// Implements AXI4-Stream protocol with back-pressure support

module linebuf_3_rv #(
    parameter WIDTH = 8,
    parameter HEIGHT = 480,
    parameter DATA_WIDTH = 24  // RGB 8-bit per channel
)(
    input  wire                     clk,
    input  wire                     rst_n,
    
    // AXI4-Stream input
    input  wire [DATA_WIDTH-1:0]    s_axis_tdata,
    input  wire                     s_axis_tvalid,
    output reg                      s_axis_tready,
    input  wire                     s_axis_tlast,
    input  wire [2:0]               s_axis_tuser,  // row, col, channel info
    
    // AXI4-Stream output - 3x3 window
    output reg  [DATA_WIDTH*9-1:0]  m_axis_tdata,  // 3x3 window
    output reg                      m_axis_tvalid,
    input  wire                     m_axis_tready,
    output reg                      m_axis_tlast,
    output reg  [2:0]               m_axis_tuser
);

    // Internal signals
    reg [DATA_WIDTH-1:0] line_buf_0 [0:HEIGHT-1];
    reg [DATA_WIDTH-1:0] line_buf_1 [0:HEIGHT-1];
    reg [DATA_WIDTH-1:0] line_buf_2 [0:HEIGHT-1];
    
    reg [9:0] col_count;
    reg [9:0] row_count;
    reg [1:0] buf_wr_ptr;  // Which buffer to write to (0,1,2)
    reg [1:0] buf_rd_ptr;  // Which buffer to read from (0,1,2)
    
    // State machine
    reg [2:0] state;
    localparam IDLE = 3'd0;
    localparam FILLING = 3'd1;
    localparam PROCESSING = 3'd2;
    
    // Output registers
    reg [DATA_WIDTH-1:0] window [0:8];  // 3x3 window
    
    // Ready/valid handshake logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axis_tready <= 1'b0;
            m_axis_tvalid <= 1'b0;
            m_axis_tlast <= 1'b0;
            m_axis_tuser <= 3'd0;
            m_axis_tdata <= {DATA_WIDTH*9{1'b0}};
            
            col_count <= 10'd0;
            row_count <= 10'd0;
            buf_wr_ptr <= 2'd0;
            buf_rd_ptr <= 2'd0;
            state <= IDLE;
        end else begin
            case (state)
                IDLE: begin
                    s_axis_tready <= 1'b1;
                    m_axis_tvalid <= 1'b0;
                    state <= FILLING;
                end
                
                FILLING: begin
                    // Fill first 3 lines
                    if (s_axis_tvalid && s_axis_tready) begin
                        case (buf_wr_ptr)
                            2'd0: line_buf_0[col_count] <= s_axis_tdata;
                            2'd1: line_buf_1[col_count] <= s_axis_tdata;
                            2'd2: line_buf_2[col_count] <= s_axis_tdata;
                        endcase
                        
                        if (s_axis_tlast) begin
                            col_count <= 10'd0;
                            row_count <= row_count + 1'b1;
                            buf_wr_ptr <= buf_wr_ptr + 1'b1;
                            
                            if (buf_wr_ptr == 2'd2) begin
                                state <= PROCESSING;
                                s_axis_tready <= 1'b0;
                            end
                        end else begin
                            col_count <= col_count + 1'b1;
                        end
                    end
                end
                
                PROCESSING: begin
                    // Generate 3x3 window and output
                    if (!m_axis_tvalid || (m_axis_tvalid && m_axis_tready)) begin
                        // Build 3x3 window
                        if (col_count > 0 && col_count < HEIGHT-1) begin
                            // Top row
                            window[0] <= line_buf_0[col_count-1];
                            window[1] <= line_buf_0[col_count];
                            window[2] <= line_buf_0[col_count+1];
                            
                            // Middle row
                            window[3] <= line_buf_1[col_count-1];
                            window[4] <= line_buf_1[col_count];
                            window[5] <= line_buf_1[col_count+1];
                            
                            // Bottom row
                            window[6] <= line_buf_2[col_count-1];
                            window[7] <= line_buf_2[col_count];
                            window[8] <= line_buf_2[col_count+1];
                            
                            // Output the window
                            m_axis_tdata <= {window[8], window[7], window[6], 
                                           window[5], window[4], window[3], 
                                           window[2], window[1], window[0]};
                            m_axis_tvalid <= 1'b1;
                            m_axis_tuser <= 3'd0;
                            
                            // Check for end of line
                            if (col_count == HEIGHT-2) begin
                                m_axis_tlast <= 1'b1;
                                col_count <= 10'd0;
                                row_count <= row_count + 1'b1;
                                
                                // Shift buffers
                                line_buf_0 <= line_buf_1;
                                line_buf_1 <= line_buf_2;
                                
                                // Read new line into buf_2
                                if (s_axis_tvalid) begin
                                    line_buf_2[col_count] <= s_axis_tdata;
                                    s_axis_tready <= 1'b1;
                                end
                            end else begin
                                col_count <= col_count + 1'b1;
                                m_axis_tlast <= 1'b0;
                            end
                        end
                    end
                end
            endcase
        end
    end

endmodule

