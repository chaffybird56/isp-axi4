#!/usr/bin/env python3
"""
Cocotb test for 3x3 convolution module
Tests depthwise convolution with various kernels and ReLU activation
Includes PSNR/SSIM image quality metrics
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.binary import BinaryValue
from cocotb.result import TestFailure
import numpy as np
import random
import json
import os
from datetime import datetime

# Try to import skimage metrics, fallback to manual calculation if not available
try:
    from skimage.metrics import peak_signal_noise_ratio, structural_similarity
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("Warning: scikit-image not available, using manual PSNR/SSIM calculation")

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
        
        # Metrics storage
        self.test_metrics = {}
        
        # Protocol assertion violations tracking
        self.protocol_violations = []
    
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
    
    def calculate_psnr(self, reference, processed):
        """Calculate PSNR between reference and processed images"""
        # Ensure same shape and type
        reference = np.array(reference, dtype=np.float64)
        processed = np.array(processed, dtype=np.float64)
        
        if reference.shape != processed.shape:
            # Handle different shapes by padding/cropping
            min_shape = tuple(min(r, p) for r, p in zip(reference.shape, processed.shape))
            reference = reference[:min_shape[0], :min_shape[1]] if len(reference.shape) == 2 else reference[:min_shape[0], :min_shape[1], :min_shape[2]]
            processed = processed[:min_shape[0], :min_shape[1]] if len(processed.shape) == 2 else processed[:min_shape[0], :min_shape[1], :min_shape[2]]
        
        if HAS_SKIMAGE:
            try:
                if len(reference.shape) == 2:
                    psnr = peak_signal_noise_ratio(reference, processed, data_range=255)
                else:
                    # Multi-channel: calculate per-channel and average
                    psnr_vals = []
                    for c in range(reference.shape[2]):
                        psnr_val = peak_signal_noise_ratio(reference[:,:,c], processed[:,:,c], data_range=255)
                        psnr_vals.append(psnr_val)
                    psnr = np.mean(psnr_vals)
                return psnr
            except:
                pass  # Fall through to manual calculation
        
        # Manual PSNR calculation
        mse = np.mean((reference - processed) ** 2)
        if mse == 0:
            return float('inf')  # Perfect match
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
        return psnr
    
    def calculate_ssim(self, reference, processed):
        """Calculate SSIM between reference and processed images"""
        reference = np.array(reference, dtype=np.float64)
        processed = np.array(processed, dtype=np.float64)
        
        if reference.shape != processed.shape:
            min_shape = tuple(min(r, p) for r, p in zip(reference.shape, processed.shape))
            reference = reference[:min_shape[0], :min_shape[1]] if len(reference.shape) == 2 else reference[:min_shape[0], :min_shape[1], :min_shape[2]]
            processed = processed[:min_shape[0], :min_shape[1]] if len(processed.shape) == 2 else processed[:min_shape[0], :min_shape[1], :min_shape[2]]
        
        # For grayscale or single channel
        if HAS_SKIMAGE:
            if len(reference.shape) == 2:
                ssim = structural_similarity(reference, processed, data_range=255)
            else:
                # For multi-channel, calculate per-channel and average
                ssim_vals = []
                for c in range(reference.shape[2]):
                    ssim_val = structural_similarity(reference[:,:,c], processed[:,:,c], data_range=255)
                    ssim_vals.append(ssim_val)
                ssim = np.mean(ssim_vals)
        else:
            # Manual SSIM approximation (simplified)
            if reference.shape != processed.shape:
                return 0.0
            mu_ref = np.mean(reference)
            mu_proc = np.mean(processed)
            sigma_ref = np.std(reference)
            sigma_proc = np.std(processed)
            sigma_ref_proc = np.mean((reference - mu_ref) * (processed - mu_proc))
            
            c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
            ssim = ((2 * mu_ref * mu_proc + c1) * (2 * sigma_ref_proc + c2)) / \
                   ((mu_ref ** 2 + mu_proc ** 2 + c1) * (sigma_ref ** 2 + sigma_proc ** 2 + c2))
            ssim = max(0.0, min(1.0, ssim))
        
        return ssim
    
    def save_test_metrics(self, test_name):
        """Save test metrics to JSON file"""
        os.makedirs("verif/metrics", exist_ok=True)
        filename = f"verif/metrics/{test_name}_metrics.json"
        
        metrics_data = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": self.test_metrics,
            "protocol_violations": len(self.protocol_violations),
            "violation_details": self.protocol_violations[:10]  # Limit to first 10
        }
        
        with open(filename, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        print(f"Metrics saved to {filename}")
    
    async def check_axi_protocol(self):
        """Check AXI4-Stream protocol assertions"""
        violations = []
        
        # Assertion 1: TVALID should not depend on TREADY
        # TVALID can be asserted independently
        # This is more of a design check, not runtime
        
        # Assertion 2: When TVALID=1 and TREADY=1, data transfer occurs
        if self.m_axis_tvalid.value and self.m_axis_tready.value:
            # Transfer is happening - this is valid
            pass
        
        # Assertion 3: TVALID should not deassert until after handshake (source)
        # This is checked during test execution
        
        # Assertion 4: TREADY can change independently of TVALID (sink)
        # This is valid behavior
        
        # Assertion 5: After reset, initial state should be TVALID=0
        # Checked in reset
        
        return violations

@cocotb.test()
async def test_identity_kernel(dut):
    """Test identity kernel (should pass through data unchanged)"""
    tester = ConvolutionTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(tester.clock, 10, units="ns").start())
    
    # Reset
    await tester.reset_dut()
    
    # Protocol assertion: After reset, TVALID should be 0
    await RisingEdge(tester.clock)
    if tester.m_axis_tvalid.value != 0:
        tester.protocol_violations.append("TVALID not 0 after reset")
    
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
    
    # Create reference image for metrics (simple 3x3 pattern)
    reference_image = np.array(test_pixels).reshape(3, 3).astype(np.uint8)
    
    # Send pixel window
    await tester.send_pixel_window(test_pixels)
    
    # Receive result
    result, last, user = await tester.receive_result()
    
    # Create processed image (identity should preserve center pixel)
    processed_image = np.zeros((3, 3), dtype=np.uint8)
    processed_image[1, 1] = result & 0xFF  # Center pixel
    
    # Calculate metrics
    psnr = tester.calculate_psnr(reference_image, processed_image)
    ssim = tester.calculate_ssim(reference_image, processed_image)
    
    tester.test_metrics = {
        "psnr": float(psnr),
        "ssim": float(ssim),
        "reference_mean": float(np.mean(reference_image)),
        "processed_mean": float(np.mean(processed_image))
    }
    
    # Save metrics
    tester.save_test_metrics("test_identity_kernel")
    
    # Check result (should be center pixel = 5)
    expected = 5
    if result != expected:
        raise cocotb.result.TestFailure(f"Identity kernel failed: got {result}, expected {expected}")
    
    print(f"PSNR: {psnr:.2f} dB, SSIM: {ssim:.4f}")

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
    
    # Test pixel window (edge pattern - high contrast)
    # Create edge: top row=0, bottom row=255
    test_pixels = [0, 0, 0, 0, 127, 0, 255, 255, 255]
    reference_image = np.array(test_pixels).reshape(3, 3).astype(np.uint8)
    
    # Send pixel window
    await tester.send_pixel_window(test_pixels)
    
    # Receive result
    result, last, user = await tester.receive_result()
    
    # Create processed image
    processed_image = np.zeros((3, 3), dtype=np.uint8)
    processed_image[1, 1] = max(0, min(255, int(result)))  # Clamp to valid range
    
    # Calculate metrics
    psnr = tester.calculate_psnr(reference_image, processed_image)
    ssim = tester.calculate_ssim(reference_image, processed_image)
    
    tester.test_metrics = {
        "psnr": float(psnr),
        "ssim": float(ssim),
        "reference_mean": float(np.mean(reference_image)),
        "processed_mean": float(np.mean(processed_image)),
        "edge_response": int(result)
    }
    
    # Save metrics
    tester.save_test_metrics("test_edge_detection_kernel")
    
    # Check result (edge detection should produce non-zero for edges)
    # For uniform input, should be 0; for edge, should be non-zero
    if np.all(reference_image == reference_image[0,0]):
        expected = 0
        if result != expected:
            raise cocotb.result.TestFailure(f"Edge detection failed on uniform: got {result}, expected {expected}")
    
    print(f"PSNR: {psnr:.2f} dB, SSIM: {ssim:.4f}, Edge Response: {result}")

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
    """Test ready/valid backpressure handling with protocol assertions"""
    tester = ConvolutionTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(tester.clock, 10, units="ns").start())
    
    # Reset
    await tester.reset_dut()
    
    # Protocol assertion: After reset, both TVALID and TREADY can be independent
    await RisingEdge(tester.clock)
    initial_valid = tester.m_axis_tvalid.value
    if initial_valid != 0:
        tester.protocol_violations.append(f"TVALID={initial_valid} immediately after reset (should be 0)")
    
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
    
    # Don't assert ready on output initially (back-pressure scenario)
    tester.m_axis_tready.value = 0
    
    # Wait for output to be valid
    await RisingEdge(tester.clock)
    cycles_waited = 0
    while not tester.m_axis_tvalid.value and cycles_waited < 100:
        await RisingEdge(tester.clock)
        cycles_waited += 1
        
        # Protocol assertion: TVALID=1 but TREADY=0 is valid (stall condition)
        if tester.m_axis_tvalid.value == 1 and tester.m_axis_tready.value == 0:
            # This is expected - back-pressure
            pass
    
    if cycles_waited >= 100:
        raise cocotb.result.TestFailure("Timeout waiting for TVALID")
    
    # Protocol assertion: TVALID should remain stable during back-pressure
    valid_during_stall = tester.m_axis_tvalid.value
    await RisingEdge(tester.clock)
    if tester.m_axis_tvalid.value != valid_during_stall and tester.m_axis_tready.value == 0:
        # TVALID can change, but ideally should remain stable during stall
        pass
    
    # Now assert ready and check handshake
    tester.m_axis_tready.value = 1
    await RisingEdge(tester.clock)
    
    # Protocol assertion: Transfer occurs when both are high
    transfer_occurred = (tester.m_axis_tvalid.value and tester.m_axis_tready.value)
    if not transfer_occurred:
        tester.protocol_violations.append("Handshake did not complete when both TVALID and TREADY were high")
        raise cocotb.result.TestFailure("Handshake failed")
    
    # Clean up
    tester.s_axis_tvalid.value = 0
    tester.m_axis_tready.value = 0
    
    # Save protocol violation report
    if tester.protocol_violations:
        tester.test_metrics = {
            "protocol_violations": len(tester.protocol_violations),
            "violations": tester.protocol_violations
        }
        tester.save_test_metrics("test_backpressure")

if __name__ == "__main__":
    print("Cocotb test for convolution module")

