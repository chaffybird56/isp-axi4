#!/usr/bin/env python3
"""Generate README screenshots without running Streamlit."""

from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "screenshots"
DEMO = ROOT / "demo_images"


class ISPProcessor:
    def __init__(self):
        self.kernel = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.float32)

    def set_kernel(self, k00, k01, k02, k10, k11, k12, k20, k21, k22):
        self.kernel = np.array(
            [[k00, k01, k02], [k10, k11, k12], [k20, k21, k22]], dtype=np.float32
        )

    def process_image(self, image: np.ndarray) -> np.ndarray:
        img_float = image.astype(np.float32)
        channels = []
        for c in range(3):
            channels.append(cv2.filter2D(img_float[:, :, c], -1, self.kernel))
        return np.clip(np.stack(channels, axis=2), 0, 255).astype(np.uint8)


def load_checkerboard() -> np.ndarray:
    img = np.array(Image.open(DEMO / "checkerboard.png").convert("RGB"))
    h, w = img.shape[:2]
    if max(h, w) > 480:
        s = 480 / max(h, w)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img


def save_aligned_comparison(out_path: Path) -> None:
    proc = ISPProcessor()
    proc.set_kernel(-1, -1, -1, -1, 8, -1, -1, -1, -1)
    inp = load_checkerboard()
    out = proc.process_image(inp)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].imshow(inp)
    axes[0].set_title("Input (checkerboard)", fontsize=13, fontweight="bold")
    axes[0].axis("off")
    axes[1].imshow(out)
    axes[1].set_title("Edge-enhanced output (3×3 kernel)", fontsize=13, fontweight="bold")
    axes[1].axis("off")
    fig.suptitle("ISP-AI pipeline — reference image processing", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_axi_handshake(out_path: Path) -> None:
    rng = np.random.default_rng(42)
    tvalid = (rng.random(80) > 0.08).astype(int)
    tready = (rng.random(80) > 0.04).astype(int)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 4))
    ax1.step(range(len(tvalid)), tvalid, where="post", color="#2E86AB", linewidth=2, label="TVALID")
    ax1.set_ylabel("TVALID")
    ax1.set_ylim(-0.1, 1.1)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax2.step(range(len(tready)), tready, where="post", color="#28A745", linewidth=2, label="TREADY")
    ax2.set_ylabel("TREADY")
    ax2.set_xlabel("Clock cycles")
    ax2.set_ylim(-0.1, 1.1)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    fig.suptitle("AXI4-Stream handshake (simulated traffic)", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_pipeline_diagram(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 2.2))
    ax.axis("off")
    boxes = [
        "RGB in\n(AXI4-Stream)",
        "Line buffer\n3×3 window",
        "Depthwise\n3×3 conv",
        "Pointwise\n1×1",
        "RGB out",
    ]
    xs = np.linspace(0.05, 0.85, len(boxes))
    for x, label in zip(xs, boxes):
        ax.add_patch(
            plt.Rectangle((x, 0.25), 0.12, 0.5, fc="#667eea", ec="#2c3e50", lw=1.5, alpha=0.9)
        )
        ax.text(x + 0.06, 0.5, label, ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    for i in range(len(boxes) - 1):
        ax.annotate(
            "",
            xy=(xs[i + 1], 0.5),
            xytext=(xs[i] + 0.12, 0.5),
            arrowprops=dict(arrowstyle="->", color="#34495e", lw=2),
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    save_aligned_comparison(SCREENSHOTS / "screenshot-aligned-images.png")
    save_axi_handshake(SCREENSHOTS / "screenshot-axi-handshake-only.png")
    save_pipeline_diagram(SCREENSHOTS / "screenshot-pipeline-architecture.png")
    print(f"Updated screenshots in {SCREENSHOTS}/")


if __name__ == "__main__":
    main()
