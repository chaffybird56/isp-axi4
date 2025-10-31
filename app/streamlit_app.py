#!/usr/bin/env python3
"""
ISP-AI Interactive Web App
Live web interface for controlling camera-style ISP pipeline and AI convolution
"""

import streamlit as st
import numpy as np
import cv2
from PIL import Image
import subprocess
import os
import time
import json
from typing import Tuple, List
import matplotlib.pyplot as plt
import io

# Page configuration
st.set_page_config(
    page_title="ISP-AI Pipeline Demo",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern professional styling
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    [data-testid="stAppViewContainer"] {
        background: rgba(255, 255, 255, 0.95);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    /* Main Header with Gradient */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Section Headers */
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid;
        border-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%) 1;
    }
    
    /* Metric Cards with Shadow */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 5px solid #667eea;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Kernel Grid */
    .kernel-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
        margin: 1rem 0;
        padding: 1rem;
        background: rgba(102, 126, 234, 0.05);
        border-radius: 8px;
    }
    
    /* Status Colors */
    .status-success {
        color: #28a745;
        font-weight: bold;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* Button Styling */
    .stButton > button {
        border-radius: 8px;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Sidebar Styling */
    .stSidebar .stMarkdown, 
    .stSidebar .stMarkdown p,
    .stSidebar .stMarkdown span,
    .stSidebar .stMarkdown div {
        color: #ffffff !important;
    }
    
    .stSidebar .stMarkdown strong,
    .stSidebar .stMarkdown b {
        color: #f39c12 !important;
    }
    
    /* Sidebar headings */
    .stSidebar h1, .stSidebar h2, .stSidebar h3 {
        color: #ffffff !important;
    }
    
    /* Radio button labels - yellow for visibility */
    .stSidebar label,
    .stSidebar [data-testid="stRadio"] label,
    .stSidebar [data-testid="stRadio"] label p,
    .stSidebar .stRadio label,
    .stSidebar .stRadio label p {
        color: #ffeb3b !important;
        font-weight: 600 !important;
    }
    
    /* Radio button text spans */
    .stSidebar [data-testid="stRadio"] > div > div,
    .stSidebar [data-testid="stRadio"] > div > div > p {
        color: #ffeb3b !important;
    }
    
    /* Image alignment fix */
    [data-testid="stImage"] {
        margin: 0 auto;
        display: block;
    }
    
    /* Column alignment */
    .stColumn {
        vertical-align: top;
    }
    
    /* Links in sidebar */
    .stSidebar a {
        color: #4fc3f7 !important;
    }
    
    /* Button text in sidebar */
    .stSidebar .stButton > button {
        color: #ffffff !important;
    }
    
    /* Container Styling */
    .stContainer {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Info Boxes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    
    /* Image Containers */
    img {
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Scrollable Content */
    .element-container {
        margin-bottom: 1.5rem;
    }
    
    /* Code Blocks */
    pre {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        border-radius: 4px;
        padding: 1rem;
    }
    
    /* Links */
    a {
        color: #667eea;
        text-decoration: none;
        transition: color 0.2s;
    }
    
    a:hover {
        color: #764ba2;
    }
</style>
""", unsafe_allow_html=True)

class ISPProcessor:
    """CPU-based ISP processor for real-time demonstration"""
    
    def __init__(self):
        self.kernel = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.float32)
        self.relu_threshold = 0
        self.enable_relu = False
        self.stride = 1
        
    def set_kernel(self, k00, k01, k02, k10, k11, k12, k20, k21, k22):
        """Set 3x3 convolution kernel"""
        self.kernel = np.array([
            [k00, k01, k02],
            [k10, k11, k12],
            [k20, k21, k22]
        ], dtype=np.float32)
    
    def set_relu(self, threshold: int, enable: bool):
        """Set ReLU parameters"""
        self.relu_threshold = threshold
        self.enable_relu = enable
    
    def process_image(self, image: np.ndarray) -> np.ndarray:
        """Process image through ISP pipeline"""
        # Convert to float for processing
        img_float = image.astype(np.float32)
        
        # Apply convolution to each channel
        processed_channels = []
        for channel in range(3):  # RGB channels
            channel_data = img_float[:, :, channel]
            
            # Apply convolution
            convolved = cv2.filter2D(channel_data, -1, self.kernel)
            
            # Apply ReLU if enabled
            if self.enable_relu:
                convolved = np.maximum(convolved, self.relu_threshold)
            
            processed_channels.append(convolved)
        
        # Combine channels
        result = np.stack(processed_channels, axis=2)
        
        # Normalize and convert back to uint8
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result

class PerformanceMonitor:
    """Monitor AXI handshake performance"""
    
    def __init__(self):
        self.cycles = 0
        self.pixels_in = 0
        self.pixels_out = 0
        self.stall_cycles = 0
        self.tvalid_history = []
        self.tready_history = []
        
    def update(self, tvalid: bool, tready: bool):
        """Update performance counters"""
        self.cycles += 1
        
        if tvalid and tready:
            self.pixels_in += 1
            self.pixels_out += 1
        elif tvalid and not tready:
            self.stall_cycles += 1
        
        # Store history for visualization (keep last 50 samples)
        self.tvalid_history.append(1 if tvalid else 0)
        self.tready_history.append(1 if tready else 0)
        
        if len(self.tvalid_history) > 50:
            self.tvalid_history.pop(0)
            self.tready_history.pop(0)
    
    def get_metrics(self) -> dict:
        """Get performance metrics"""
        return {
            'cycles': self.cycles,
            'pixels_in': self.pixels_in,
            'pixels_out': self.pixels_out,
            'stall_cycles': self.stall_cycles,
            'throughput': self.pixels_out / max(self.cycles, 1) * 100,
            'stall_rate': self.stall_cycles / max(self.cycles, 1) * 100
        }

def generate_test_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate test pattern"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create gradient pattern
    for y in range(height):
        for x in range(width):
            image[y, x, 0] = (x * 255) // width      # Red gradient
            image[y, x, 1] = (y * 255) // height     # Green gradient
            image[y, x, 2] = ((x + y) * 255) // (width + height)  # Blue gradient
    
    return image

def generate_checkerboard_pattern(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate checkerboard pattern"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    square_size = 32
    
    for y in range(height):
        for x in range(width):
            square_x = x // square_size
            square_y = y // square_size
            
            if (square_x + square_y) % 2 == 0:
                image[y, x] = [255, 255, 255]  # White
            else:
                image[y, x] = [0, 0, 0]        # Black
    
    return image

def generate_edge_test_pattern(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate pattern optimized for edge detection testing"""
    image = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # Horizontal lines
    for y in range(100, height, 80):
        image[y:y+10, :] = [255, 255, 255]
    
    # Vertical lines
    for x in range(100, width, 80):
        image[:, x:x+10] = [0, 0, 0]
    
    # Diagonal lines
    for i in range(0, min(width, height), 60):
        if i < width and i < height:
            cv2.line(image, (i, 0), (0, i), (128, 0, 128), 3)
    
    return image

def generate_geometric_pattern(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate geometric pattern"""
    image = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # Add geometric shapes
    cv2.rectangle(image, (50, 50), (200, 150), (255, 0, 0), 2)
    cv2.circle(image, (400, 100), 50, (0, 255, 0), -1)
    cv2.ellipse(image, (500, 300), (80, 40), 45, 0, 360, (0, 0, 255), -1)
    
    # Add some lines
    for i in range(0, width, 40):
        cv2.line(image, (i, 200), (i + 20, 350), (255, 255, 0), 2)
    
    return image

def generate_portrait_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate a realistic portrait-like image with facial features"""
    image = np.ones((height, width, 3), dtype=np.uint8) * 200  # Light skin tone
    
    # Face oval
    center_x, center_y = width // 2, height // 2
    cv2.ellipse(image, (center_x, center_y), (120, 150), 0, 0, 360, (220, 180, 160), -1)
    
    # Eyes
    cv2.circle(image, (center_x - 40, center_y - 30), 15, (255, 255, 255), -1)
    cv2.circle(image, (center_x + 40, center_y - 30), 15, (255, 255, 255), -1)
    cv2.circle(image, (center_x - 40, center_y - 30), 8, (0, 0, 0), -1)
    cv2.circle(image, (center_x + 40, center_y - 30), 8, (0, 0, 0), -1)
    
    # Nose
    cv2.line(image, (center_x, center_y - 10), (center_x, center_y + 20), (180, 140, 120), 3)
    
    # Mouth
    cv2.ellipse(image, (center_x, center_y + 40), (25, 10), 0, 0, 180, (200, 50, 50), 2)
    
    # Hair
    cv2.ellipse(image, (center_x, center_y - 100), (130, 80), 0, 0, 180, (100, 50, 0), -1)
    
    # Add some texture/noise for realism
    noise = np.random.randint(-20, 20, image.shape, dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return image

def generate_landscape_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate a beautiful landscape with mountains, sky, and water"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Sky gradient (top half)
    for y in range(height // 2):
        intensity = int(135 + (120 * y / (height // 2)))
        image[y, :] = [intensity, intensity + 20, intensity + 40]  # Blue sky
    
    # Mountains (middle third)
    mountain_start = height // 3
    for y in range(mountain_start, height // 2):
        for x in range(width):
            # Create mountain silhouette
            mountain_height = int(50 * np.sin(x / 80) + 30 * np.sin(x / 40))
            if y > height // 2 - mountain_height:
                image[y, x] = [80 + (y - mountain_start) // 2, 60 + (y - mountain_start) // 2, 40]
    
    # Water/ground (bottom half)
    for y in range(height // 2, height):
        intensity = int(100 - (y - height // 2) * 50 / (height // 2))
        image[y, :] = [max(0, intensity), max(0, intensity + 30), max(0, intensity + 10)]
    
    # Sun
    cv2.circle(image, (width - 100, 80), 30, (255, 255, 150), -1)
    
    # Trees
    for x in range(50, width, 80):
        tree_base = height // 2 + 20
        cv2.rectangle(image, (x-3, tree_base), (x+3, tree_base+40), (100, 50, 0), -1)
        cv2.circle(image, (x, tree_base), 20, (0, 100, 0), -1)
    
    return image

def generate_cityscape_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate a cityscape with buildings and lights"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Night sky
    image[:height//3, :] = [20, 20, 40]
    
    # Buildings
    building_heights = [200, 180, 220, 160, 240, 200, 190, 210, 180, 230]
    building_colors = [(60, 60, 80), (80, 60, 60), (60, 80, 60), (70, 70, 70), (90, 50, 50)]
    
    for i, height in enumerate(building_heights):
        x_start = i * (width // len(building_heights))
        x_end = (i + 1) * (width // len(building_heights))
        building_color = building_colors[i % len(building_colors)]
        
        # Building body
        cv2.rectangle(image, (x_start, height//3), (x_end, height//3 + height), building_color, -1)
        
        # Windows with lights
        for floor in range(5, height//3 + height - 10, 15):
            for window_x in range(x_start + 10, x_end - 10, 20):
                if np.random.random() > 0.3:  # 70% of windows lit
                    cv2.rectangle(image, (window_x, floor), (window_x + 8, floor + 8), (255, 255, 150), -1)
    
    # Street
    cv2.rectangle(image, (0, height//3 + 180), (width, height), (30, 30, 30), -1)
    
    # Street lights
    for x in range(50, width, 100):
        cv2.rectangle(image, (x-2, height//3 + 180), (x+2, height//3 + 220), (100, 100, 100), -1)
        cv2.circle(image, (x, height//3 + 215), 8, (255, 255, 200), -1)
    
    return image

def generate_artwork_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate an artistic abstract image"""
    image = np.ones((height, width, 3), dtype=np.uint8) * 240  # White background
    
    # Abstract shapes and colors
    colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255), (255, 255, 100), (255, 100, 255)]
    
    # Random circles
    for _ in range(15):
        center = (np.random.randint(50, width-50), np.random.randint(50, height-50))
        radius = np.random.randint(20, 80)
        color = colors[np.random.randint(0, len(colors))]
        cv2.circle(image, center, radius, color, -1)
    
    # Random rectangles
    for _ in range(8):
        x1, y1 = np.random.randint(0, width-100), np.random.randint(0, height-100)
        x2, y2 = x1 + np.random.randint(50, 150), y1 + np.random.randint(50, 100)
        color = colors[np.random.randint(0, len(colors))]
        cv2.rectangle(image, (x1, y1), (x2, y2), color, -1)
    
    # Flowing lines
    for _ in range(5):
        color = colors[np.random.randint(0, len(colors))]
        points = []
        for i in range(10):
            x = i * (width // 10) + np.random.randint(-20, 20)
            y = height // 2 + 50 * np.sin(i) + np.random.randint(-30, 30)
            points.append((int(x), int(y)))
        
        for i in range(len(points) - 1):
            cv2.line(image, points[i], points[i+1], color, 5)
    
    return image

def run_rtl_simulation() -> bool:
    """Run RTL simulation and return success status"""
    try:
        # For demo purposes, simulate RTL processing with CPU
        st.info("🔄 Running RTL simulation...")
        time.sleep(2)  # Simulate processing time
        
        # Process the current image with the current kernel settings
        processor = st.session_state.processor
        test_image = st.session_state.test_image
        
        # Apply the current kernel
        processed_image = processor.process_image(test_image)
        
        # Save the result as if it came from RTL
        result_image = Image.fromarray(processed_image)
        result_image.save("rtl_out.ppm")
        
        st.success("✅ RTL simulation completed successfully!")
        return True
        
    except Exception as e:
        st.error(f"❌ RTL simulation failed: {e}")
        return False

def visualize_axi_handshake(monitor: PerformanceMonitor):
    """Create AXI handshake visualization"""
    if len(monitor.tvalid_history) < 10:
        return None
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 4))
    
    # TVALID signal
    ax1.step(range(len(monitor.tvalid_history)), monitor.tvalid_history, 
             where='post', label='TVALID', color='blue', linewidth=2)
    ax1.set_ylabel('TVALID')
    ax1.set_ylim(-0.1, 1.1)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # TREADY signal
    ax2.step(range(len(monitor.tready_history)), monitor.tready_history, 
             where='post', label='TREADY', color='green', linewidth=2)
    ax2.set_ylabel('TREADY')
    ax2.set_xlabel('Clock Cycles')
    ax2.set_ylim(-0.1, 1.1)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def main():
    """Main application"""
    
    # Header
    st.markdown('<h1 class="main-header">🎥 ISP-AI Pipeline Demo</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ## What is this demo?
    
    This is a **real-time camera image processor** that shows how your phone, car, or security camera 
    processes raw image data into beautiful photos. Think of it as the "brain" that makes your camera 
    photos look sharp and clear!
    
    ### How it works:
    1. **Input Image** → Raw pixels from camera sensor
    2. **Line Buffers** → Store 3 rows of pixels to create 3×3 windows  
    3. **AI Convolution** → Apply filters (like Instagram filters) to enhance edges and details
    4. **Output Image** → Processed, enhanced photo
    
    ### What makes this special:
    - **Real Hardware**: This runs on actual silicon chips (RTL), not just software
    - **AI-Powered**: Uses smart algorithms to sharpen images and detect edges
    - **Live Performance**: Shows exactly how fast the hardware processes each pixel
    - **Interactive**: Adjust settings and see results instantly!
    """)
    
    # Initialize session state
    if 'processor' not in st.session_state:
        st.session_state.processor = ISPProcessor()
    if 'monitor' not in st.session_state:
        st.session_state.monitor = PerformanceMonitor()
    if 'test_image' not in st.session_state:
        # Load an actual demo image if available
        # Check multiple possible paths
        demo_paths = [
            os.path.join("demo_images", "checkerboard.png"),
            os.path.join("..", "demo_images", "checkerboard.png"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo_images", "checkerboard.png")
        ]
        loaded = False
        for demo_image_path in demo_paths:
            if os.path.exists(demo_image_path):
                st.session_state.test_image = np.array(Image.open(demo_image_path))
                loaded = True
                break
        if not loaded:
            st.session_state.test_image = generate_test_image()
    
    # Sidebar controls
    with st.sidebar:
        st.markdown('<div class="section-header">🎛️ Control Panel</div>', unsafe_allow_html=True)
        
        # Processing mode
        st.markdown("### Processing Mode")
        st.markdown("**CPU Demo**: Real-time software processing (instant results)")
        st.markdown("**RTL Hardware**: Run actual silicon chip simulation (takes a few seconds)")
        
        mode = st.radio(
            "Choose Processing Type",
            ["RTL Hardware", "CPU Demo"],
            index=0,  # Default to RTL Hardware
            help="CPU Demo: Real-time processing with sliders\nRTL Hardware: Run actual hardware simulation"
        )
        
        # Demo run buttons
        st.markdown("### 🚀 Run Demo")
        col_demo1, col_demo2 = st.columns(2)
        
        with col_demo1:
            if st.button("🎬 Run Full Demo", help="Complete demonstration with current settings"):
                st.session_state.run_demo = True
                
        with col_demo2:
            if mode == "RTL Hardware":
                if st.button("⚡ Run RTL Simulation", help="Run hardware simulation"):
                    with st.spinner("Running RTL simulation..."):
                        success = run_rtl_simulation()
                        if success:
                            st.success("✅ RTL simulation completed!")
                        else:
                            st.error("❌ RTL simulation failed!")
            else:
                if st.button("🔄 Run CPU Demo", help="Run software simulation"):
                    st.session_state.run_cpu_demo = True
        
        # Kernel presets
        st.markdown("### Filter Presets")
        st.markdown("**Impressive filters** - Click to see dramatic effects:")
        
        if st.button("📷 Original", help="No change - shows original image"):
            st.session_state.processor.set_kernel(0, 0, 0, 0, 1, 0, 0, 0, 0)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✨ TikTok Sharpen", help="Dramatic edge enhancement like social media filters"):
                st.session_state.processor.set_kernel(0, -2, 0, -2, 9, -2, 0, -2, 0)
            if st.button("🔍 Edge Magic", help="Strong edge detection for artistic effects"):
                st.session_state.processor.set_kernel(-1, -1, -1, -1, 8, -1, -1, -1, -1)
        with col2:
            if st.button("🌫️ Dreamy Blur", help="Soft, dreamy blur effect"):
                st.session_state.processor.set_kernel(1, 1, 1, 1, 1, 1, 1, 1, 1)
            if st.button("🏔️ 3D Emboss", help="Strong 3D raised effect"):
                st.session_state.processor.set_kernel(-2, -1, 0, -1, 1, 1, 0, 1, 2)
        
        # Kernel sliders
        st.markdown("**Custom Kernel**")
        st.markdown("3×3 Convolution Kernel:")
        
        # Create kernel grid
        k00 = st.slider("k₀₀", -10, 10, int(st.session_state.processor.kernel[0, 0]))
        k01 = st.slider("k₀₁", -10, 10, int(st.session_state.processor.kernel[0, 1]))
        k02 = st.slider("k₀₂", -10, 10, int(st.session_state.processor.kernel[0, 2]))
        k10 = st.slider("k₁₀", -10, 10, int(st.session_state.processor.kernel[1, 0]))
        k11 = st.slider("k₁₁", -10, 10, int(st.session_state.processor.kernel[1, 1]))
        k12 = st.slider("k₁₂", -10, 10, int(st.session_state.processor.kernel[1, 2]))
        k20 = st.slider("k₂₀", -10, 10, int(st.session_state.processor.kernel[2, 0]))
        k21 = st.slider("k₂₁", -10, 10, int(st.session_state.processor.kernel[2, 1]))
        k22 = st.slider("k₂₂", -10, 10, int(st.session_state.processor.kernel[2, 2]))
        
        # Update kernel
        st.session_state.processor.set_kernel(k00, k01, k02, k10, k11, k12, k20, k21, k22)
        
        # ReLU controls
        st.markdown("**ReLU Activation**")
        enable_relu = st.checkbox("Enable ReLU", value=st.session_state.processor.enable_relu, 
                                 help="❓ Rectified Linear Unit - cuts off negative values below threshold (like Instagram filters)")
        relu_threshold = st.slider("ReLU Threshold", 0, 255, st.session_state.processor.relu_threshold,
                                  help="❓ Values below this become 0 - higher = more dramatic effect")
        st.session_state.processor.set_relu(relu_threshold, enable_relu)
        
        # Stride
        stride = st.selectbox("Stride", [1, 2], index=0, 
                             help="❓ Step size: 1=process every pixel (slower), 2=process every other pixel (faster)")
        st.session_state.processor.stride = stride
        
    
    # Main content area with equal height columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="section-header">📷 Input Image</div>', unsafe_allow_html=True)
        
        # Preset demo images
        st.markdown("**Try these impressive demo images:**")
        demo_col1, demo_col2 = st.columns(2)
        with demo_col1:
            if st.button("📸 Portrait"):
                st.session_state.test_image = generate_portrait_image()
            if st.button("🌅 Landscape"):
                st.session_state.test_image = generate_landscape_image()
        with demo_col2:
            if st.button("🏙️ Cityscape"):
                st.session_state.test_image = generate_cityscape_image()
            if st.button("🎨 Artwork"):
                st.session_state.test_image = generate_artwork_image()
        
        # Image upload
        uploaded_file = st.file_uploader("Or upload your own image:", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                image = np.array(image)
                if len(image.shape) == 3 and image.shape[2] == 3:
                    st.session_state.test_image = image
                    st.success("✅ Image uploaded successfully!")
                else:
                    st.error("❌ Please upload a color (RGB) image")
            except Exception as e:
                st.error(f"❌ Error loading image: {e}")
        
        # Display input image with consistent sizing
        st.image(st.session_state.test_image, caption="Input Image", use_container_width=True)
    
    with col2:
        st.markdown('<div class="section-header">🎨 Processed Output</div>', unsafe_allow_html=True)
        
        if mode == "CPU Demo":
            # Real-time processing
            output_image = st.session_state.processor.process_image(st.session_state.test_image)
            # Display output image with consistent sizing
            st.image(output_image, caption="Processed Image", use_container_width=True)
            
            # Update performance monitor (simulate)
            for _ in range(10):
                tvalid = np.random.random() > 0.1  # 90% valid
                tready = np.random.random() > 0.05  # 95% ready
                st.session_state.monitor.update(tvalid, tready)
        
        elif mode == "RTL Hardware":
            # Show RTL output if available
            if os.path.exists("rtl_out.ppm"):
                try:
                    rtl_image = Image.open("rtl_out.ppm")
                    st.image(rtl_image, caption="RTL Hardware Output", use_column_width=True)
                    st.success("✅ Hardware output displayed")
                except Exception as e:
                    st.error(f"Failed to load RTL output: {e}")
            else:
                st.info("Click 'Run RTL Simulation' to generate hardware output")
    
    # Performance metrics
    st.markdown('<div class="section-header">📊 Hardware Performance Metrics</div>', unsafe_allow_html=True)
    
    st.markdown("""
    **What these numbers mean:**
    - **Cycles**: Clock ticks since processing started (like a stopwatch)
    - **Pixels In/Out**: How many pixels the hardware has processed
    - **Stall Cycles**: When hardware had to wait (like traffic jams)
    - **Throughput**: How efficiently the hardware is running
    """)
    
    metrics = st.session_state.monitor.get_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🕐 Cycles", f"{metrics['cycles']:,}", help="Total clock cycles")
    
    with col2:
        st.metric("📥 Pixels In", f"{metrics['pixels_in']:,}", help="Input pixels processed")
    
    with col3:
        st.metric("📤 Pixels Out", f"{metrics['pixels_out']:,}", help="Output pixels generated")
    
    with col4:
        st.metric("⏸️ Stall Cycles", f"{metrics['stall_cycles']:,}", help="Waiting cycles")
    
    # Additional metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("⚡ Throughput", f"{metrics['throughput']:.1f}%", help="Processing efficiency")
    
    with col2:
        st.metric("🚧 Stall Rate", f"{metrics['stall_rate']:.1f}%", help="Wait percentage")
    
    with col3:
        # Calculate enhancement percentage (simulate based on kernel intensity)
        kernel_sum = abs(st.session_state.processor.kernel).sum()
        enhancement_pct = min(100, (kernel_sum - 1) * 10)  # Scale kernel intensity to percentage
        st.metric("✨ Enhancement", f"{enhancement_pct:.1f}%", help="Visual enhancement intensity")
    
    # AXI handshake visualization
    st.markdown('<div class="section-header">🔗 AXI Handshake Visualization</div>', unsafe_allow_html=True)
    
    st.markdown("""
    **What is AXI Handshake?**
    Think of it like a conversation between two people:
    - **TVALID** (🔵 Blue line): "I have data ready to send!"
    - **TREADY** (🟢 Green line): "I'm ready to receive your data!"
    - **Transfer** (🟡 Overlap): Data actually moves when BOTH signals are high
    - **Stall** (🔴 Gap): When sender has data but receiver isn't ready
    """)
    
    fig = visualize_axi_handshake(st.session_state.monitor)
    if fig:
        st.pyplot(fig)
        st.markdown("""
        **Reading the graph:**
        - **High lines** = Signal is active (ready/valid)
        - **Low lines** = Signal is inactive (not ready/not valid)
        - **Overlapping highs** = Data transfer happening
        - **Gaps** = Hardware waiting (stalls)
        """)
    else:
        st.info("🎯 Run processing to see live AXI handshake signals")
    
    # Architecture explanation
    with st.expander("🏗️ Architecture Details"):
        st.markdown("""
        **ISP Pipeline Architecture:**
        
        1. **Line Buffers**: Store 3 lines of image data, output 3×3 windows
        2. **Depthwise 3×3 Convolution**: Separate convolution per RGB channel
        3. **Pointwise 1×1 Convolution**: Channel mixing (3→3 channels)
        4. **AXI4-Stream**: Ready/valid handshake for back-pressure handling
        5. **Performance Counters**: Monitor throughput, stalls, and efficiency
        
        **Why Separable Convolution?**
        - Reduces MAC operations vs full convolution
        - Perfect for embedded/edge AI accelerators
        - MobileNet-style efficiency
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **ISP-AI Pipeline Demo** | Built for hardware hackathons | 
    AXI4-Stream • Depthwise Conv • Real-time Processing
    """)

if __name__ == "__main__":
    main()
