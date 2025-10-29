#!/usr/bin/env python3
"""
Cocotb test for 3x3 convolution module
Tests depthwise convolution with various kernels and ReLU activation
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.binary import BinaryValue
import numpy as np
import random

class ConvolutionTester:
    def __init__(self, dut):
        self.dut = dut
        self.clock = dut.clk
        self.reset = dut.rst_n
        
        # Input signals
        self.s_axis_tdata = dut.s_axis_tdata
        self.s_axis_tvalid = dut.s_axis_tvalid
        self.s_axis_tready = dut.s_axis_tready
        self.s_axis_tlast = dut.s_axis_tlast
        self.s_axis_tuser = dut.s_axis_tuser
        
        # Output signals
        self.m_axis_tdata = dut.m_axis_tdata
        self.m_axis_tvalid = dut.m_axis_tvalid
        self.m_axis_tready = dut.m_axis_tready
        self.m_axis_tlast = dut.m_axis_tlast
        self.m_axis_tuser = dut.m_axis_tuser
        
        # Control signals
        self.kernel_00 = dut.kernel_00
        self.kernel_01 = dut.kernel_01
        self.kernel_02 = dut.kernel_02
        self.kernel_10 = dut.kernel_10
        self.kernel_11 = dut.kernel_11
        self.kernel_12 = dut.kernel_12
        self.kernel_20 = dut.kernel_20
        self.kernel_21 = dut.kernel_21
        self.kernel_22 = dut.kernel_22
        self.relu_threshold = dut.relu_threshold
        self.stride = dut.stride
        self.enable_relu = dut.enable_relu
    
    async def reset_dut(self):
        """Reset the DUT"""
        self.reset.value = 0
        await RisingEdge(self.clock)
        await RisingEdge(self.clock)
        self.reset.value = 1
        await RisingEdge(self.clock)
    
    async def send_pixel_window(self, pixels, last=0, user=0):
        """Send a 3x3 pixel window to the convolution"""
        # Pack 9 pixels into tdata
        pixel_data = 0
        for i, pixel in enumerate(pixels):
            pixel_data |= (pixel & 0xFF) << (i * 8)
        
        self.s_axis_tdata.value = pixel_data
        self.s_axis_tvalid.value = 1
        self.s_axis_tlast.value = last
        self.s_axis_tuser.value = user
        
        # Wait for handshake
        await RisingEdge(self.clock)
        while not (self.s_axis_tvalid.value and self.s_axis_tready.value):
            await RisingEdge(self.clock)
        
        self.s_axis_tvalid.value = 0
    
    async def receive_result(self, timeout=100):
        """Receive convolution result"""
        timeout_count = 0
        while not self.m_axis_tvalid.value and timeout_count < timeout:
            await RisingEdge(self.clock)
            timeout_count += 1
        
        if timeout_count >= timeout:
            raise cocotb.result.TestFailure("Timeout waiting for result")
        
        # Wait for handshake
        self.m_axis_tready.value = 1
        await RisingEdge(self.clock)
        
        result = self.m_axis_tdata.value
        last = self.m_axis_tlast.value
        user = self.m_axis_tuser.value
        
        self.m_axis_tready.value = 0
        
        return result, last, user
    
    def set_kernel(self, kernel):
        """Set convolution kernel"""
        self.kernel_00.value = kernel[0][0] & 0xFF
        self.kernel_01.value = kernel[0][1] & 0xFF
        self.kernel_02.value = kernel[0][2] & 0xFF
        self.kernel_10.value = kernel[1][0] & 0xFF
        self.kernel_11.value = kernel[1][1] & 0xFF
        self.kernel_12.value = kernel[1][2] & 0xFF
        self.kernel_20.value = kernel[2][0] & 0xFF
        self.kernel_21.value = kernel[2][1] & 0xFF
        self.kernel_22.value = kernel[2][2] & 0xFF

@cocotb.test()
async def test_identity_kernel(dut):
    """Test identity kernel (should pass through data unchanged)"""
    tester = ConvolutionTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(tester.clock, 10, units="ns").start())
    
    # Reset
    await tester.reset_dut()
    
    # Set identity kernel
    identity_kernel = [
        [0, 0, 0],
        [0, 1, 0],
        [0, 0, 0]
    ]
    tester.set_kernel(identity_kernel)
    tester.enable_relu.value = 0
    tester.stride.value = 1
    tester.relu_threshold.value = 0
    
    # Test pixel window
    test_pixels = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    
    # Send pixel window
    await tester.send_pixel_window(test_pixels)
    
    # Receive result
    result, last, user = await tester.receive_result()
    
    # Check result (should be center pixel = 5)
    expected = 5
    if result != expected:
        raise cocotb.result.TestFailure(f"Identity kernel failed: got {result}, expected {expected}")

@cocotb.test()
async def test_edge_detection_kernel(dut):
    """Test edge detection kernel"""
    tester = ConvolutionTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(tester.clock, 10, units="ns").start())
    
    # Reset
    await tester.reset_dut()
    
    # Set edge detection kernel
    edge_kernel = [
        [-1, -1, -1],
        [-1,  8, -1],
        [-1, -1, -1]
    ]
    tester.set_kernel(edge_kernel)
    tester.enable_relu.value = 0
    tester.stride.value = 1
    tester.relu_threshold.value = 0
    
    # Test pixel window (uniform)
    test_pixels = [10, 10, 10, 10, 10, 10, 10, 10, 10]
    
    # Send pixel window
    await tester.send_pixel_window(test_pixels)
    
    # Receive result
    result, last, user = await tester.receive_result()
    
    # Check result (should be 0 for uniform input)
    expected = 0
    if result != expected:
        raise cocotb.result.TestFailure(f"Edge detection failed: got {result}, expected {expected}")

@cocotb.test()
async def test_relu_activation(dut):
    """Test ReLU activation"""
    tester = ConvolutionTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(tester.clock, 10, units="ns").start())
    
    # Reset
    await tester.reset_dut()
    
    # Set kernel that produces negative result
    negative_kernel = [
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1]
    ]
    tester.set_kernel(negative_kernel)
    tester.enable_relu.value = 1
    tester.stride.value = 1
    tester.relu_threshold.value = 5  # Threshold at 5
    
    # Test pixel window
    test_pixels = [0, 0, 0, 0, 1, 0, 0, 0, 0]  # Should produce small result
    
    # Send pixel window
    await tester.send_pixel_window(test_pixels)
    
    # Receive result
    result, last, user = await tester.receive_result()
    
    # Check result (should be clamped to threshold)
    if result < tester.relu_threshold.value:
        raise cocotb.result.TestFailure(f"ReLU failed: got {result}, expected >= {tester.relu_threshold.value}")

@cocotb.test()
async def test_backpressure(dut):
    """Test ready/valid backpressure handling"""
    tester = ConvolutionTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(tester.clock, 10, units="ns").start())
    
    # Reset
    await tester.reset_dut()
    
    # Set simple kernel
    identity_kernel = [
        [0, 0, 0],
        [0, 1, 0],
        [0, 0, 0]
    ]
    tester.set_kernel(identity_kernel)
    tester.enable_relu.value = 0
    
    # Start sending data
    tester.s_axis_tdata.value = 0x050505050505050505  # All 5s
    tester.s_axis_tvalid.value = 1
    tester.s_axis_tlast.value = 0
    tester.s_axis_tuser.value = 0
    
    # Don't assert ready on output initially
    tester.m_axis_tready.value = 0
    
    # Wait for output to be valid
    await RisingEdge(tester.clock)
    while not tester.m_axis_tvalid.value:
        await RisingEdge(tester.clock)
    
    # Now assert ready and check handshake
    tester.m_axis_tready.value = 1
    await RisingEdge(tester.clock)
    
    # Check that data was transferred
    if not (tester.m_axis_tvalid.value and tester.m_axis_tready.value):
        raise cocotb.result.TestFailure("Handshake failed")
    
    # Clean up
    tester.s_axis_tvalid.value = 0
    tester.m_axis_tready.value = 0

if __name__ == "__main__":
    print("Cocotb test for convolution module")

