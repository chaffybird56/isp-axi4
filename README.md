# 🎥 ISP-AI Pipeline Demo

**Live demonstration of camera ISP pipeline with AI separable convolution**

A comprehensive hardware hackathon project showcasing a complete ISP (Image Signal Processor) pipeline with depthwise separable convolution, AXI4-Stream protocol, and real-time web interface.

## 🏆 Why This Wins at Hackathons

- **Visual Impact**: Live web app with instant image processing updates
- **Hardware Depth**: Complete RTL design with AXI4-Stream, verification, and synthesis
- **Real-time Demo**: Interactive sliders control hardware parameters instantly
- **Performance Visualization**: Live AXI handshake monitoring and throughput counters
- **Production Ready**: Docker containerized, comprehensive build system

## 🎯 Project Goals

Show the audience something they can see change, while quietly proving the "hard stuff":

- **Live Web Interface**: Sliders/toggles drive camera-style ISP pipeline
- **AI Convolution**: Depthwise 3×3 + pointwise 1×1 separable convolution
- **Real Hardware**: AXI4-Stream ready/valid back-pressure, Yosys synthesis
- **Performance Metrics**: Throughput counters and AXI handshake visualization
- **Complete Stack**: RTL → Verification → Synthesis → Web Demo

## 🏗️ Architecture

### Hardware Pipeline
```
Input Image → Line Buffers (3-line) → Depthwise 3×3 Conv → Pointwise 1×1 → Output
                    ↓                         ↓                    ↓
               AXI4-Stream              AXI4-Stream         AXI4-Stream
               Ready/Valid              Ready/Valid         Ready/Valid
```

### Key Components
- **Line Buffers**: 3-line window generation for 3×3 convolution
- **Depthwise Conv**: Separate 3×3 convolution per RGB channel
- **Pointwise Conv**: 1×1 channel mixing (3→3 channels)
- **AXI4-Lite**: Control registers and performance counters
- **AXI4-Stream**: Data flow with back-pressure support

### Why Separable Convolution?
- **Efficiency**: Reduces MAC operations vs full convolution
- **Embedded Friendly**: Perfect for edge AI accelerators
- **MobileNet Style**: Industry-proven efficiency pattern

## 🚀 Quick Start

### 1) Build & Run (Docker)
```bash
# Build Docker image
docker build -t isp-ai .

# Run container with web interface
docker run --rm -it -p 8501:8501 \
  -v $PWD:/workspace \
  -v $PWD/out:/mnt/data \
  isp-ai

# Inside container
make ui    # Launch web app at http://localhost:8501
```

### 2) Local Development
```bash
# Install dependencies
make install-deps

# Launch web interface
make ui

# Run verification
make test

# Synthesize design
make synth

# Generate demo images
make demo
```

## 📁 Project Structure

```
isp-ai/
├── rtl/                    # RTL source files
│   ├── ai/                 # AI/convolution cores
│   │   ├── linebuf_3_rv.v      # 3-line buffer with ready/valid
│   │   ├── conv3x3_int8_rv.v   # Depthwise 3x3 convolution
│   │   └── conv1x1_pointwise.v # Pointwise 1x1 mixing
│   └── axi/                # AXI interfaces
│       ├── axi4l_regs_ext.v    # AXI4-Lite registers + counters
│       └── axi4s_rgb_dw_pw_top.v # Top-level module
├── sim/                    # Simulation
│   ├── tb_linebuf.sv           # Icarus testbench
│   └── rtl_dump_main.cpp       # Verilator C++ harness
├── verif/                  # Verification
│   └── test_conv.py            # Cocotb tests
├── synth/                  # Synthesis
│   └── run_yosys.ys           # Yosys synthesis script
├── pd/                     # Place & Route (optional)
│   ├── sta.tcl                 # OpenROAD STA script
│   └── Makefile               # PD build system
├── app/                    # Web application
│   └── streamlit_app.py       # Interactive Streamlit UI
├── tools/                  # Utilities
│   └── gen_demo_image.py      # Demo image generator
├── Dockerfile              # Container definition
├── Makefile               # Build system
└── README.md              # This file
```

## 🎛️ Web Interface Features

### Control Panel
- **Kernel Presets**: Identity, Sharpen, Edge Detection, Blur, Emboss
- **Custom Kernel**: 9 sliders for 3×3 convolution matrix
- **ReLU Controls**: Threshold and enable/disable
- **Processing Modes**: CPU demo vs RTL hardware simulation

### Real-time Processing
- **Instant Updates**: Sliders update output immediately
- **Side-by-side View**: Input and processed images
- **Performance Metrics**: Cycles, pixels in/out, stall cycles
- **AXI Visualization**: Live TVALID/TREADY handshake display

### Hardware Integration
- **RTL Simulation**: Button to run actual hardware
- **Hardware Output**: Display real RTL-processed images
- **Performance Counters**: Live hardware metrics

## 🔧 Technical Details

### AXI4-Stream Protocol
**Data transfer only occurs when both TVALID=1 AND TREADY=1**
- **TVALID**: Source indicates data is valid
- **TREADY**: Sink indicates ready to accept data
- **Back-pressure**: When TVALID=1 but TREADY=0 (stall)
- **Performance**: Monitors throughput and stall rates

### ISP Pipeline Stages
1. **Line Buffers**: Store 3 image lines, output 3×3 windows
2. **Depthwise 3×3**: Separate convolution per RGB channel
3. **Pointwise 1×1**: Channel mixing with configurable weights
4. **AXI4-Lite Control**: Register interface for parameters

### Performance Counters
- **Cycles**: Total clock cycles
- **Pixels In**: Input pixels processed
- **Pixels Out**: Output pixels generated
- **Stall Cycles**: Back-pressure events
- **Throughput**: Effective processing rate
- **Stall Rate**: Back-pressure percentage

## 🛠️ Build Targets

```bash
make ui        # Launch Streamlit web app
make test      # Run cocotb verification
make sim       # Run Icarus testbenches
make synth     # Yosys synthesis
make rtl_sim   # Verilator hardware simulation
make demo      # Generate demo images
make clean     # Clean generated files
```

## 🧪 Verification

### Cocotb Tests
- **Identity Kernel**: Pass-through verification
- **Edge Detection**: Kernel functionality test
- **ReLU Activation**: Threshold clamping test
- **Back-pressure**: Ready/valid protocol test

### Icarus Simulation
- **Line Buffer**: 3×3 window generation
- **Gradient Test**: Synthetic pattern processing
- **Handshake Verification**: AXI protocol compliance

### Hardware-in-the-Loop
- **Verilator C++**: Real RTL simulation
- **PPM Output**: Hardware-processed images
- **Performance Monitoring**: Live hardware metrics

## 📊 Synthesis & Analysis

### Yosys Synthesis
```bash
make synth     # Run synthesis
# Results in synth/synth.log
```

### OpenROAD Place & Route (Optional)
```bash
make pd        # Run place & route
# Results in pd/reports/
```

## 🎨 Demo Images

Generate test patterns:
```bash
make demo
# Creates demo_images/ with various test patterns
```

Available patterns:
- **Gradient**: RGB color gradients
- **Checkerboard**: High-contrast pattern
- **Noise**: Random pattern with structure
- **Edge Test**: Optimized for edge detection
- **Text Pattern**: Geometric shapes and lines

## 🌐 Web Interface Usage

### Basic Usage
1. **Upload Image** or use default test pattern
2. **Select Preset** or adjust custom kernel sliders
3. **Configure ReLU** threshold and enable
4. **Watch Output** update in real-time
5. **Monitor Performance** metrics and AXI signals

### Advanced Features
- **RTL Mode**: Switch to hardware simulation
- **Run Simulation**: Execute actual RTL
- **View Hardware Output**: See real hardware results
- **Performance Analysis**: Monitor throughput and stalls

## 🔬 What's an ISP?

**Image Signal Processor** - Hardware that converts raw sensor data into display-ready images:

1. **Demosaic**: Convert raw sensor data to RGB
2. **Color Correction**: Adjust color balance and saturation
3. **Gamma Correction**: Apply tone mapping
4. **Noise Reduction**: Filter out sensor noise
5. **Sharpening**: Enhance edge detail

**Everywhere**: Phones, cars, robots, industrial cameras, security systems.

## 🧠 AI Integration

### Separable Convolution Benefits
- **Fewer MACs**: 3×3 + 1×1 vs 3×3 full convolution
- **Channel Efficiency**: Process each channel separately
- **Mobile Optimized**: MobileNet-style efficiency
- **Embedded Friendly**: Perfect for edge AI accelerators

### Why This Matters
- **Real-time Processing**: Hardware acceleration for AI
- **Power Efficiency**: Optimized for mobile/embedded
- **Scalability**: Easy to extend with more AI layers

## 🏁 Live Demo Script

### For Judges/Demo
1. **Open Web App**: Show live interface
2. **Upload Photo**: Demonstrate real image processing
3. **Adjust Sliders**: Show instant kernel effects
4. **Switch to RTL**: Run actual hardware simulation
5. **Show Performance**: Explain AXI handshake and metrics
6. **Open Synthesis**: Display area/timing reports

### Key Talking Points
- **Visual Impact**: "See the image change instantly"
- **Hardware Depth**: "This runs on actual RTL hardware"
- **AXI Protocol**: "Industry-standard AXI4-Stream with back-pressure"
- **AI Efficiency**: "Separable convolution reduces operations by 8x"
- **Production Ready**: "Complete verification and synthesis flow"

## 🚀 Stretch Goals

- **AXI-Lite Programming**: UI-controlled weight programming
- **Live Camera**: WebRTC integration for real-time camera
- **BRAM Integration**: Replace line buffers with BRAM primitives
- **Real PDK**: OpenROAD with actual technology libraries
- **Coverage Analysis**: Functional coverage reporting

## 📚 References

- **AXI4-Stream Spec**: ARM AMBA specification
- **MobileNet Paper**: Separable convolution efficiency
- **Yosys Manual**: Synthesis and optimization
- **Verilator Guide**: Hardware simulation
- **Streamlit Docs**: Web app framework

## 🤝 Contributing

This is a hackathon demonstration project. Key areas for extension:
- Additional convolution kernels
- More ISP pipeline stages
- Enhanced verification coverage
- Real-time camera integration
- Performance optimization

## 📄 License

MIT License - Feel free to use for hackathons, education, and projects.

---

**ISP-AI Pipeline Demo** | Built for hardware hackathons | AXI4-Stream • Depthwise Conv • Real-time Processing

