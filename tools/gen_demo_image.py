#!/usr/bin/env python3
"""
Generate demo images for ISP-AI pipeline testing
Creates various test patterns and synthetic images
"""

import numpy as np
import cv2
from PIL import Image
import argparse
import os

def generate_gradient(width=640, height=480):
    """Generate RGB gradient test pattern"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            image[y, x, 0] = (x * 255) // width      # Red gradient
            image[y, x, 1] = (y * 255) // height     # Green gradient
            image[y, x, 2] = ((x + y) * 255) // (width + height)  # Blue gradient
    
    return image

def generate_checkerboard(width=640, height=480, square_size=32):
    """Generate checkerboard pattern"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            square_x = x // square_size
            square_y = y // square_size
            
            if (square_x + square_y) % 2 == 0:
                image[y, x] = [255, 255, 255]  # White
            else:
                image[y, x] = [0, 0, 0]        # Black
    
    return image

def generate_noise(width=640, height=480, noise_level=50):
    """Generate noise pattern"""
    image = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    
    # Add some structure
    for y in range(0, height, 64):
        for x in range(0, width, 64):
            cv2.circle(image, (x + 32, y + 32), 16, (128, 128, 128), -1)
    
    return image

def generate_text_pattern(width=640, height=480):
    """Generate pattern with text"""
    image = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # Add some geometric shapes
    cv2.rectangle(image, (50, 50), (200, 150), (255, 0, 0), 2)
    cv2.circle(image, (400, 100), 50, (0, 255, 0), -1)
    cv2.ellipse(image, (500, 300), (80, 40), 45, 0, 360, (0, 0, 255), -1)
    
    # Add some lines
    for i in range(0, width, 40):
        cv2.line(image, (i, 200), (i + 20, 350), (255, 255, 0), 2)
    
    return image

def generate_edge_test(width=640, height=480):
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
        cv2.line(image, (i, 0), (0, i), (128, 0, 128), 3)
    
    return image

def apply_kernel(image, kernel, normalize=True):
    """Apply convolution kernel to image"""
    if normalize:
        # Normalize kernel to sum to 1 (for smoothing) or 0 (for edge detection)
        kernel_sum = np.sum(kernel)
        if kernel_sum != 0:
            kernel = kernel / kernel_sum
    
    # Apply to each channel
    result = np.zeros_like(image, dtype=np.float32)
    for channel in range(3):
        result[:, :, channel] = cv2.filter2D(
            image[:, :, channel].astype(np.float32), -1, kernel
        )
    
    return np.clip(result, 0, 255).astype(np.uint8)

def main():
    parser = argparse.ArgumentParser(description="Generate demo images for ISP-AI pipeline")
    parser.add_argument("--width", type=int, default=640, help="Image width")
    parser.add_argument("--height", type=int, default=480, help="Image height")
    parser.add_argument("--output", type=str, default="demo_images", help="Output directory")
    parser.add_argument("--all", action="store_true", help="Generate all test patterns")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Generate test patterns
    patterns = {
        "gradient": generate_gradient(args.width, args.height),
        "checkerboard": generate_checkerboard(args.width, args.height),
        "noise": generate_noise(args.width, args.height),
        "text_pattern": generate_text_pattern(args.width, args.height),
        "edge_test": generate_edge_test(args.width, args.height)
    }
    
    # Save images
    for name, image in patterns.items():
        filename = os.path.join(args.output, f"{name}.png")
        Image.fromarray(image).save(filename)
        print(f"Generated: {filename}")
    
    # Generate some processed examples
    print("\nGenerating processed examples...")
    
    # Edge detection on edge test
    edge_kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]], dtype=np.float32)
    edge_result = apply_kernel(patterns["edge_test"], edge_kernel, normalize=False)
    Image.fromarray(edge_result).save(os.path.join(args.output, "edge_detected.png"))
    print("Generated: edge_detected.png")
    
    # Blur on checkerboard
    blur_kernel = np.ones((5, 5), dtype=np.float32) / 25
    blur_result = apply_kernel(patterns["checkerboard"], blur_kernel)
    Image.fromarray(blur_result).save(os.path.join(args.output, "blurred.png"))
    print("Generated: blurred.png")
    
    # Sharpen on text pattern
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpen_result = apply_kernel(patterns["text_pattern"], sharpen_kernel, normalize=False)
    Image.fromarray(sharpen_result).save(os.path.join(args.output, "sharpened.png"))
    print("Generated: sharpened.png")
    
    print(f"\nAll demo images saved to: {args.output}/")
    print("Use these images to test the ISP pipeline with various input patterns.")

if __name__ == "__main__":
    main()

