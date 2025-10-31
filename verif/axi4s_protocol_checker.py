#!/usr/bin/env python3
"""
Cocotb-based AXI4-Stream protocol checker
Provides runtime assertions for TVALID/TREADY handshake protocol
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.result import TestFailure

class AXI4SProtocolChecker:
    """Runtime protocol checker for AXI4-Stream interface"""
    
    def __init__(self, dut, clock, reset, prefix=""):
        """
        Initialize protocol checker
        
        Args:
            dut: Device under test
            clock: Clock signal
            reset: Reset signal
            prefix: Signal prefix ('s_axis_' or 'm_axis_')
        """
        self.dut = dut
        self.clock = clock
        self.reset = reset
        self.prefix = prefix
        
        # Get AXI4-Stream signals
        self.tvalid = getattr(dut, f"{prefix}tvalid", None)
        self.tready = getattr(dut, f"{prefix}tready", None)
        self.tdata = getattr(dut, f"{prefix}tdata", None)
        self.tlast = getattr(dut, f"{prefix}tlast", None)
        self.tuser = getattr(dut, f"{prefix}tuser", None)
        
        # State tracking
        self.violations = []
        self.transfer_count = 0
        self.stall_count = 0
        
        # Previous state for edge detection
        self.prev_valid = 0
        self.prev_ready = 0
        self.prev_data = 0
        
    async def check_reset_state(self):
        """Assertion: After reset, TVALID should be 0"""
        await RisingEdge(self.clock)
        if self.tvalid.value != 0:
            self.violations.append({
                "time": cocotb.simulator.get_sim_time(),
                "assertion": "reset_valid_low",
                "message": f"{self.prefix}tvalid not 0 after reset"
            })
            raise TestFailure(f"{self.prefix}tvalid should be 0 after reset")
    
    async def monitor_handshake(self):
        """Continuously monitor handshake protocol"""
        while True:
            await RisingEdge(self.clock)
            
            if not self.reset.value:
                continue  # Skip during reset
            
            valid = int(self.tvalid.value)
            ready = int(self.tready.value) if self.tready else 0
            
            # Assertion: Transfer occurs when both TVALID and TREADY are high
            if valid and ready:
                self.transfer_count += 1
                self.prev_valid = valid
                self.prev_ready = ready
                if self.tdata:
                    self.prev_data = int(self.tdata.value)
                continue
            
            # Assertion: Stall condition (TVALID=1, TREADY=0)
            if valid and not ready:
                self.stall_count += 1
                
                # Assertion: Data should remain stable during back-pressure
                if self.tdata and int(self.tdata.value) != self.prev_data and self.prev_valid:
                    self.violations.append({
                        "time": cocotb.simulator.get_sim_time(),
                        "assertion": "data_stable_during_stall",
                        "message": f"{self.prefix}tdata changed during back-pressure"
                    })
            
            # Assertion: TVALID should not deassert until after handshake
            if self.prev_valid and not valid and not self.prev_ready:
                self.violations.append({
                    "time": cocotb.simulator.get_sim_time(),
                    "assertion": "valid_stable_until_ready",
                    "message": f"{self.prefix}tvalid deasserted before handshake"
                })
            
            self.prev_valid = valid
            self.prev_ready = ready
    
    def get_statistics(self):
        """Get protocol statistics"""
        return {
            "transfers": self.transfer_count,
            "stalls": self.stall_count,
            "violations": len(self.violations),
            "violation_details": self.violations[:10]  # Limit details
        }
    
    def clear_violations(self):
        """Clear violation history"""
        self.violations = []
        self.transfer_count = 0
        self.stall_count = 0

