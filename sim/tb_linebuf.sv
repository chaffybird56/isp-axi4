// Testbench for line buffer module
// Tests 3-line window generation with ready/valid handshake

module tb_linebuf;

    // Parameters
    parameter WIDTH = 640;
    parameter HEIGHT = 480;
    parameter DATA_WIDTH = 8;
    
    // Clock and reset
    reg clk;
    reg rst_n;
    
    // Testbench signals
    reg [DATA_WIDTH-1:0] test_data;
    reg test_valid;
    wire test_ready;
    reg test_last;
    reg [2:0] test_user;
    
    wire [DATA_WIDTH*9-1:0] window_data;
    wire window_valid;
    reg window_ready;
    wire window_last;
    wire [2:0] window_user;
    
    // Stimulus
    reg [9:0] pixel_count;
    reg [9:0] line_count;
    
    // Instantiate DUT
    linebuf_3_rv #(
        .WIDTH(WIDTH),
        .HEIGHT(HEIGHT),
        .DATA_WIDTH(DATA_WIDTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_tdata(test_data),
        .s_axis_tvalid(test_valid),
        .s_axis_tready(test_ready),
        .s_axis_tlast(test_last),
        .s_axis_tuser(test_user),
        .m_axis_tdata(window_data),
        .m_axis_tvalid(window_valid),
        .m_axis_tready(window_ready),
        .m_axis_tlast(window_last),
        .m_axis_tuser(window_user)
    );
    
    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    // Test stimulus
    initial begin
        // Initialize signals
        rst_n = 0;
        test_data = 0;
        test_valid = 0;
        test_last = 0;
        test_user = 0;
        window_ready = 1;
        pixel_count = 0;
        line_count = 0;
        
        // Reset
        #20;
        rst_n = 1;
        #10;
        
        $display("Starting line buffer test...");
        
        // Send test pattern
        for (line_count = 0; line_count < 3; line_count = line_count + 1) begin
            $display("Sending line %d", line_count);
            
            for (pixel_count = 0; pixel_count < WIDTH; pixel_count = pixel_count + 1) begin
                @(posedge clk);
                
                // Generate test pattern (gradient)
                test_data = (line_count * WIDTH + pixel_count) & 8'hFF;
                test_valid = 1;
                test_user = line_count;
                
                // Last pixel of line
                if (pixel_count == WIDTH - 1) begin
                    test_last = 1;
                end else begin
                    test_last = 0;
                end
                
                // Wait for handshake
                wait(test_valid && test_ready);
            end
            
            @(posedge clk);
            test_valid = 0;
            test_last = 0;
        end
        
        $display("Input data sent, waiting for window outputs...");
        
        // Collect window outputs
        repeat(1000) begin
            @(posedge clk);
            if (window_valid && window_ready) begin
                $display("Window received: %h %h %h %h %h %h %h %h %h",
                    window_data[DATA_WIDTH*1-1:DATA_WIDTH*0],
                    window_data[DATA_WIDTH*2-1:DATA_WIDTH*1],
                    window_data[DATA_WIDTH*3-1:DATA_WIDTH*2],
                    window_data[DATA_WIDTH*4-1:DATA_WIDTH*3],
                    window_data[DATA_WIDTH*5-1:DATA_WIDTH*4],
                    window_data[DATA_WIDTH*6-1:DATA_WIDTH*5],
                    window_data[DATA_WIDTH*7-1:DATA_WIDTH*6],
                    window_data[DATA_WIDTH*8-1:DATA_WIDTH*7],
                    window_data[DATA_WIDTH*9-1:DATA_WIDTH*8]);
            end
        end
        
        $display("Test completed");
        $finish;
    end
    
    // Monitor ready/valid handshakes
    always @(posedge clk) begin
        if (test_valid && test_ready) begin
            $display("Input handshake: data=%h, user=%d", test_data, test_user);
        end
        
        if (window_valid && window_ready) begin
            $display("Output handshake: window received");
        end
    end

endmodule

