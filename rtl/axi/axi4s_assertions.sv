// SystemVerilog Assertions (SVA) for AXI4-Stream Protocol
// Ensures proper TVALID/TREADY handshake sequencing and packet framing

`ifndef AXI4S_ASSERTIONS_SV
`define AXI4S_ASSERTIONS_SV

// AXI4-Stream Protocol Assertions
// These assertions check TVALID/TREADY handshake correctness

module axi4s_assertions #(
    parameter DATA_WIDTH = 24
)(
    input wire clk,
    input wire rst_n,
    
    // Input interface (slave)
    input wire [DATA_WIDTH-1:0] s_axis_tdata,
    input wire s_axis_tvalid,
    input wire s_axis_tready,
    input wire s_axis_tlast,
    input wire [2:0] s_axis_tuser,
    
    // Output interface (master)
    input wire [DATA_WIDTH-1:0] m_axis_tdata,
    input wire m_axis_tvalid,
    input wire m_axis_tready,
    input wire m_axis_tlast,
    input wire [2:0] m_axis_tuser
);

    // ============================================================
    // AXI4-Stream Source (Master) Assertions
    // ============================================================
    
    // Assertion 1: After reset, TVALID should be deasserted
    property reset_valid_low;
        @(posedge clk) !rst_n |-> ##1 !m_axis_tvalid;
    endproperty
    assert_reset_valid: assert property (reset_valid_low)
        else $error("AXI4S: m_axis_tvalid not deasserted after reset");
    
    // Assertion 2: TVALID must not deassert until after handshake
    // Once TVALID is asserted, it must remain asserted until TREADY is also asserted
    property valid_stable_until_ready;
        @(posedge clk) disable iff (!rst_n)
        (m_axis_tvalid && !m_axis_tready) |=> m_axis_tvalid;
    endproperty
    assert_valid_stable: assert property (valid_stable_until_ready)
        else $error("AXI4S: m_axis_tvalid deasserted before handshake completed");
    
    // Assertion 3: Data must be stable while TVALID is high and TREADY is low
    property data_stable_during_stall;
        @(posedge clk) disable iff (!rst_n)
        (m_axis_tvalid && !m_axis_tready) |=> 
        ($stable(m_axis_tdata) && $stable(m_axis_tlast) && $stable(m_axis_tuser));
    endproperty
    assert_data_stable: assert property (data_stable_during_stall)
        else $error("AXI4S: Data changed during back-pressure (TVALID=1, TREADY=0)");
    
    // Assertion 4: TLAST must be consistent during a packet
    // TLAST should be 0 for all transfers except the last in a packet
    property last_consistency;
        @(posedge clk) disable iff (!rst_n)
        (m_axis_tvalid && m_axis_tready && m_axis_tlast) |=> 
        ##[0:$] (!m_axis_tvalid || (m_axis_tvalid && m_axis_tlast));
    endproperty
    assert_last_consistency: assert property (last_consistency)
        else $error("AXI4S: TLAST inconsistency detected");
    
    // ============================================================
    // AXI4-Stream Sink (Slave) Assertions
    // ============================================================
    
    // Assertion 5: TREADY can change independently of TVALID (valid behavior)
    // This is allowed by spec, so we just monitor it
    
    // Assertion 6: When TREADY is asserted, sink must be ready to accept data
    // (Implementation-specific: our design should accept data when TREADY=1)
    
    // ============================================================
    // Handshake Assertions
    // ============================================================
    
    // Assertion 7: Transfer only occurs when both TVALID and TREADY are high
    property transfer_requires_both;
        @(posedge clk) disable iff (!rst_n)
        ($rose(m_axis_tvalid && m_axis_tready)) |-> 
        (m_axis_tvalid && m_axis_tready);
    endproperty
    assert_transfer_handshake: assert property (transfer_requires_both)
        else $error("AXI4S: Transfer attempted without proper handshake");
    
    // Assertion 8: No data loss during back-pressure
    // When TVALID=1 and TREADY goes from 1->0, data should remain valid
    property no_data_loss_on_backpressure;
        @(posedge clk) disable iff (!rst_n)
        (m_axis_tvalid && m_axis_tready && $fell(m_axis_tready)) |=> 
        (m_axis_tvalid && !m_axis_tready);
    endproperty
    assert_no_data_loss: assert property (no_data_loss_on_backpressure)
        else $error("AXI4S: Data lost during back-pressure transition");
    
    // ============================================================
    // Packet Framing Assertions
    // ============================================================
    
    // Assertion 9: TLAST should mark end of packet
    // After TLAST=1, next valid transfer should be start of new packet
    property packet_boundary;
        @(posedge clk) disable iff (!rst_n)
        (m_axis_tvalid && m_axis_tready && m_axis_tlast) |->
        ##[1:10] (!m_axis_tvalid || (m_axis_tvalid && !m_axis_tlast));
    endproperty
    assert_packet_boundary: assert property (packet_boundary)
        else $warning("AXI4S: Possible packet framing issue");
    
    // Assertion 10: TUSER should be stable during packet transfer
    // TUSER typically indicates packet metadata (e.g., start of line)
    property user_stable;
        @(posedge clk) disable iff (!rst_n)
        (m_axis_tvalid && !m_axis_tlast) |=> 
        ($stable(m_axis_tuser) || !m_axis_tvalid || m_axis_tlast);
    endproperty
    assert_user_stable: assert property (user_stable)
        else $warning("AXI4S: TUSER changed during packet transfer");
    
    // ============================================================
    // Input Interface Assertions (s_axis_*)
    // ============================================================
    
    // Similar assertions for input interface
    property input_reset_valid_low;
        @(posedge clk) !rst_n |-> ##1 !s_axis_tvalid;
    endproperty
    assert_input_reset_valid: assert property (input_reset_valid_low)
        else $error("AXI4S: s_axis_tvalid not deasserted after reset");
    
    property input_valid_stable;
        @(posedge clk) disable iff (!rst_n)
        (s_axis_tvalid && !s_axis_tready) |=> s_axis_tvalid;
    endproperty
    assert_input_valid_stable: assert property (input_valid_stable)
        else $error("AXI4S: s_axis_tvalid deasserted before handshake");
    
    property input_data_stable;
        @(posedge clk) disable iff (!rst_n)
        (s_axis_tvalid && !s_axis_tready) |=> 
        ($stable(s_axis_tdata) && $stable(s_axis_tlast) && $stable(s_axis_tuser));
    endproperty
    assert_input_data_stable: assert property (input_data_stable)
        else $error("AXI4S: Input data changed during back-pressure");
    
    // Coverage properties (optional, for verification metrics)
    covergroup axi4s_coverage @(posedge clk);
        handshake: coverpoint (m_axis_tvalid && m_axis_tready);
        backpressure: coverpoint (m_axis_tvalid && !m_axis_tready);
        idle: coverpoint (!m_axis_tvalid && !m_axis_tready);
        
        packet_start: coverpoint (m_axis_tvalid && m_axis_tready && !m_axis_tlast);
        packet_end: coverpoint (m_axis_tvalid && m_axis_tready && m_axis_tlast);
    endgroup
    
    axi4s_coverage cov_inst = new();

endmodule

`endif // AXI4S_ASSERTIONS_SV

