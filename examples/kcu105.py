#!/usr/bin/env python3

# This file is Copyright (c) 2015-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import os
import argparse

from migen import *

from litex.boards.platforms import kcu105
from litex.build.generic_platform import tools
from litex.build.xilinx import VivadoProgrammer

from litex.soc.interconnect.csr import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.export import get_csr_header, get_soc_header, get_mem_header

from litepcie.phy.uspciephy import USPCIEPHY
from litepcie.core import LitePCIeEndpoint, LitePCIeMSI
from litepcie.frontend.dma import LitePCIeDMA
from litepcie.frontend.wishbone import LitePCIeWishboneBridge

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module, AutoCSR):
    def __init__(self, platform):
        self.clock_domains.cd_sys = ClockDomain("sys")
        self.comb += self.cd_sys.clk.eq(ClockSignal("pcie"))

# LitePCIeSoC --------------------------------------------------------------------------------------

class LitePCIeSoC(SoCMini):
    mem_map = {"csr": 0x00000000}
    def __init__(self, platform):
        sys_clk_freq = int(125e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, sys_clk_freq, csr_data_width=32,
            ident="LitePCIe example design", ident_version=True)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform)

        # PCIe PHY ---------------------------------------------------------------------------------
        self.submodules.pcie_phy = USPCIEPHY(platform, platform.request("pcie_x4"))
        self.add_csr("pcie_phy")

        # PCIe Endpoint ----------------------------------------------------------------------------
        self.submodules.pcie_endpoint = LitePCIeEndpoint(self.pcie_phy)

        # PCIe Wishbone bridge ---------------------------------------------------------------------
        self.submodules.pcie_bridge = LitePCIeWishboneBridge(self.pcie_endpoint)
        self.add_wb_master(self.pcie_bridge.wishbone)

        # PCIe DMA ---------------------------------------------------------------------------------
        self.submodules.pcie_dma = LitePCIeDMA(self.pcie_phy, self.pcie_endpoint, with_loopback=True)
        self.add_csr("pcie_dma")

        # PCIe MSI ---------------------------------------------------------------------------------
        self.submodules.pcie_msi = LitePCIeMSI()
        self.add_csr("pcie_msi")
        self.comb += self.pcie_msi.source.connect(self.pcie_phy.msi)
        self.interrupts = {
            "PCIE_DMA_WRITER":    self.pcie_dma.writer.irq,
            "PCIE_DMA_READER":    self.pcie_dma.reader.irq
        }
        for i, (k, v) in enumerate(sorted(self.interrupts.items())):
            self.comb += self.pcie_msi.irqs[i].eq(v)
            self.add_constant(k + "_INTERRUPT", i)

    def generate_software_headers(self):
        csr_header = get_csr_header(self.csr_regions, self.constants, with_access_functions=False)
        tools.write_to_file(os.path.join("build", "csr.h"), csr_header)
        soc_header = get_soc_header(self.constants, with_access_functions=False)
        tools.write_to_file(os.path.join("build", "soc.h"), soc_header)
        mem_header = get_mem_header(self.mem_regions)
        tools.write_to_file(os.path.join("build", "mem.h"), mem_header)

# Load ---------------------------------------------------------------------------------------------

def load():
    prog = VivadoProgrammer()
    prog.load_bitstream("build/gateware/kcu105.bit")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="build bitstream")
    parser.add_argument("--load",  action="store_true", help="load bitstream (to SRAM)")
    args = parser.parse_args()

    platform = kcu105.Platform()
    soc     = LitePCIeSoC(platform)
    builder = Builder(soc, output_dir="build")
    builder.build(build_name="kcu105", run=args.build)
    soc.generate_software_headers()

    if args.load:
        load()

if __name__ == "__main__":
    main()
