# Verification Suite

This directory contains the verification test suite for the ISP-AI pipeline.

## Test Metrics

The test suite automatically calculates and saves image quality metrics:

### PSNR (Peak Signal-to-Noise Ratio)
- Measures image quality after processing
- Higher values indicate better quality (typically > 30 dB for good quality)
- Formula: `PSNR = 20 × log₁₀(MAX/√MSE)`

### SSIM (Structural Similarity Index)
- Measures structural similarity between reference and processed images
- Range: 0.0 to 1.0 (higher is better)
- Accounts for luminance, contrast, and structure

### Metrics Output

Test metrics are automatically saved to `verif/metrics/` after each test run:
- `test_identity_kernel_metrics.json`
- `test_edge_detection_kernel_metrics.json`
- `test_backpressure_metrics.json`

Each metrics file contains:
```json
{
  "test_name": "test_identity_kernel",
  "timestamp": "2024-10-31T...",
  "metrics": {
    "psnr": 45.2,
    "ssim": 0.95,
    "reference_mean": 127.5,
    "processed_mean": 127.5
  },
  "protocol_violations": 0
}
```

## Protocol Assertions

### SystemVerilog Assertions (SVA)
Located in `rtl/axi/axi4s_assertions.sv`, these assertions check:
- TVALID/TREADY handshake compliance
- Data stability during back-pressure
- Packet framing correctness
- Reset state verification

### Cocotb Runtime Assertions
Implemented in `test_conv.py`:
- Reset state checks
- Handshake protocol monitoring
- Back-pressure handling verification
- Transfer vs. stall counting

## Running Tests

```bash
# Run all tests with metrics collection
make test

# View generated metrics
ls -lh verif/metrics/*.json

# Run cocotb (Icarus recommended locally; CI uses same)
cd verif
SIM=icarus COCOTB_REDUCED_LOG_FMT=1 python3 run_cocotb.py
```

## Dependencies

- `cocotb`: Hardware verification framework
- `scikit-image`: For PSNR/SSIM calculations (optional, falls back to manual calculation)
- `numpy`: Numerical operations
- `pytest`: Test framework

Install with:
```bash
pip install cocotb scikit-image numpy pytest
```

