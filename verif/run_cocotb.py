#!/usr/bin/env python3
"""Run cocotb tests via cocotb_tools.runner (cocotb 2.x)."""
import os
from pathlib import Path

from cocotb_tools.runner import get_runner

VERIF = Path(__file__).resolve().parent
ROOT = VERIF.parent
RTL = ROOT / "rtl" / "ai" / "conv3x3_int8_rv.v"
TOP = "conv3x3_int8_rv"
TEST_MODULE = "test_conv"
VERILATOR_ARGS = ["-Wno-fatal", "-Wno-WIDTHEXPAND", "-Wno-CASEINCOMPLETE"]


def main() -> None:
    sim = os.getenv("SIM", "verilator")
    os.environ["PYTHONPATH"] = str(VERIF) + os.pathsep + os.environ.get("PYTHONPATH", "")

    runner = get_runner(sim)
    build_kw = dict(
        sources=[RTL],
        hdl_toplevel=TOP,
        always=True,
        timescale=("1ns", "1ps"),
    )
    if sim == "verilator":
        build_kw["build_args"] = VERILATOR_ARGS
    elif sim == "icarus":
        build_kw["build_args"] = ["-g2012"]
    runner.build(**build_kw)
    runner.test(
        hdl_toplevel=TOP,
        test_module=TEST_MODULE,
        extra_env={"PYTHONPATH": str(VERIF)},
    )


if __name__ == "__main__":
    main()
