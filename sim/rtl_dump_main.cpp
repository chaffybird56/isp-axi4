// Verilator C++ harness for hardware-in-the-loop
// Streams synthetic RGB frame through RTL and outputs PPM image

#include <verilated.h>
#include <verilated_vcd_c.h>
#include "Vaxi4s_rgb_dw_pw_top.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <cstdint>

// Image parameters
const int IMAGE_WIDTH = 640;
const int IMAGE_HEIGHT = 480;

// PPM header
void write_ppm_header(std::ofstream& file, int width, int height) {
    file << "P6\n" << width << " " << height << "\n255\n";
}

// Generate test pattern
void generate_test_pattern(std::vector<uint8_t>& image) {
    for (int y = 0; y < IMAGE_HEIGHT; y++) {
        for (int x = 0; x < IMAGE_WIDTH; x++) {
            int idx = (y * IMAGE_WIDTH + x) * 3;
            
            // Create gradient pattern
            image[idx + 0] = (x * 255) / IMAGE_WIDTH;      // Red
            image[idx + 1] = (y * 255) / IMAGE_HEIGHT;     // Green
            image[idx + 2] = ((x + y) * 255) / (IMAGE_WIDTH + IMAGE_HEIGHT); // Blue
        }
    }
}

// Simulate AXI4-Lite register writes
void configure_kernel(Vaxi4s_rgb_dw_pw_top* dut, uint8_t k00, uint8_t k01, uint8_t k02,
                     uint8_t k10, uint8_t k11, uint8_t k12,
                     uint8_t k20, uint8_t k21, uint8_t k22) {
    // Simulate register writes (simplified)
    dut->s_axi_awaddr = 0x00;  // kernel_00 address
    dut->s_axi_awvalid = 1;
    dut->s_axi_wdata = k00;
    dut->s_axi_wvalid = 1;
    dut->s_axi_wstrb = 0xF;
    
    // Wait for write handshake
    while (!(dut->s_axi_awready && dut->s_axi_wready)) {
        dut->eval();
    }
    
    dut->s_axi_awvalid = 0;
    dut->s_axi_wvalid = 0;
    
    // Continue for other kernel values...
    // (In a real implementation, you'd write all registers)
}

int main(int argc, char** argv) {
    // Initialize Verilator
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
    
    // Create instance
    Vaxi4s_rgb_dw_pw_top* dut = new Vaxi4s_rgb_dw_pw_top;
    
    // Create VCD trace
    VerilatedVcdC* trace = new VerilatedVcdC;
    dut->trace(trace, 99);
    trace->open("rtl_trace.vcd");
    
    // Initialize
    dut->clk = 0;
    dut->rst_n = 0;
    dut->s_axi_aclk = 0;
    dut->s_axi_aresetn = 0;
    
    // Reset sequence
    for (int i = 0; i < 10; i++) {
        dut->clk = !dut->clk;
        dut->s_axi_aclk = !dut->s_axi_aclk;
        dut->eval();
        trace->dump(i * 2);
    }
    
    dut->rst_n = 1;
    dut->s_axi_aresetn = 1;
    
    // Configure kernel (edge detection)
    configure_kernel(dut, 0, -1, 0, -1, 4, -1, 0, -1, 0);
    
    // Generate test pattern
    std::vector<uint8_t> input_image(IMAGE_WIDTH * IMAGE_HEIGHT * 3);
    generate_test_pattern(input_image);
    
    // Output image
    std::vector<uint8_t> output_image(IMAGE_WIDTH * IMAGE_HEIGHT * 3);
    
    // Simulation variables
    int pixel_count = 0;
    int cycle_count = 0;
    bool input_active = true;
    bool output_active = false;
    
    // AXI-Stream signals
    dut->s_axis_tvalid = 0;
    dut->s_axis_tlast = 0;
    dut->s_axis_tuser = 0;
    dut->m_axis_tready = 1;
    
    std::cout << "Starting RTL simulation..." << std::endl;
    
    // Main simulation loop
    while (pixel_count < IMAGE_WIDTH * IMAGE_HEIGHT && cycle_count < 1000000) {
        // Clock generation
        dut->clk = !dut->clk;
        dut->s_axi_aclk = !dut->s_axi_aclk;
        
        // Input side
        if (input_active && pixel_count < IMAGE_WIDTH * IMAGE_HEIGHT) {
            if (!dut->s_axis_tvalid || (dut->s_axis_tvalid && dut->s_axis_tready)) {
                int pixel_idx = pixel_count * 3;
                
                // Pack RGB data (24-bit)
                uint32_t rgb_data = (input_image[pixel_idx + 2] << 16) |
                                   (input_image[pixel_idx + 1] << 8) |
                                   input_image[pixel_idx + 0];
                
                dut->s_axis_tdata = rgb_data;
                dut->s_axis_tvalid = 1;
                
                // Check for end of line
                if ((pixel_count + 1) % IMAGE_WIDTH == 0) {
                    dut->s_axis_tlast = 1;
                } else {
                    dut->s_axis_tlast = 0;
                }
                
                dut->s_axis_tuser = pixel_count % IMAGE_WIDTH;  // Column
                
                pixel_count++;
                input_active = false;  // Wait for handshake
            }
        } else if (dut->s_axis_tvalid && dut->s_axis_tready) {
            // Handshake completed
            dut->s_axis_tvalid = 0;
            dut->s_axis_tlast = 0;
            input_active = true;
        }
        
        // Output side
        if (dut->m_axis_tvalid && dut->m_axis_tready) {
            // Extract RGB data
            uint32_t output_data = dut->m_axis_tdata;
            uint8_t r = output_data & 0xFF;
            uint8_t g = (output_data >> 8) & 0xFF;
            uint8_t b = (output_data >> 16) & 0xFF;
            
            // Store in output image (assuming we track output pixel count)
            int out_pixel = (dut->m_axis_tuser * IMAGE_WIDTH + 
                           ((dut->m_axis_tuser + 1) % IMAGE_WIDTH)) % (IMAGE_WIDTH * IMAGE_HEIGHT);
            
            if (out_pixel < IMAGE_WIDTH * IMAGE_HEIGHT) {
                int out_idx = out_pixel * 3;
                output_image[out_idx + 0] = r;
                output_image[out_idx + 1] = g;
                output_image[out_idx + 2] = b;
            }
            
            output_active = true;
        }
        
        // Evaluate
        dut->eval();
        trace->dump(cycle_count);
        
        cycle_count++;
        
        // Progress indicator
        if (cycle_count % 10000 == 0) {
            std::cout << "Cycle: " << cycle_count 
                      << ", Pixels processed: " << pixel_count << std::endl;
        }
    }
    
    std::cout << "Simulation completed in " << cycle_count << " cycles" << std::endl;
    
    // Write output PPM
    std::ofstream ppm_file("rtl_out.ppm", std::ios::binary);
    if (ppm_file.is_open()) {
        write_ppm_header(ppm_file, IMAGE_WIDTH, IMAGE_HEIGHT);
        
        for (int i = 0; i < IMAGE_WIDTH * IMAGE_HEIGHT; i++) {
            int idx = i * 3;
            ppm_file.write(reinterpret_cast<char*>(&output_image[idx]), 3);
        }
        
        ppm_file.close();
        std::cout << "Output image written to rtl_out.ppm" << std::endl;
    } else {
        std::cerr << "Failed to create output PPM file" << std::endl;
    }
    
    // Cleanup
    trace->close();
    delete dut;
    delete trace;
    
    return 0;
}

