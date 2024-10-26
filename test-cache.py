import m5

from m5.objects import *
from three_level import *

system = System()

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "2GHz"
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")] 

system.cpu = X86TimingSimpleCPU()

system.cpu.icache = L0ICache()
system.cpu.dcache = L0DCache()

system.cpu.icache.connectCPU(system.cpu)
system.cpu.dcache.connectCPU(system.cpu)

system.l1bus = L2XBar()

system.cpu.icache.connectBus(system.l1bus)
system.cpu.dcache.connectBus(system.l1bus)

system.l1cache = L1Cache()
system.l1cache.connectCPUSideBus(system.l1bus)
system.membus = SystemXBar()
system.l1cache.connectMemSideBus(system.membus)

system.cpu.createInterruptController()

system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.system_port = system.membus.cpu_side_ports

binary = 'gem5/tests/test-progs/hello/bin/x86/linux/hello'

system.workload = SEWorkload.init_compatible(binary)

process = Process()

process.cmd = [binary]

system.cpu.workload = process
system.cpu.createThreads()


root = Root(full_system=False, system=system)

m5.instantiate()

print(f"Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")