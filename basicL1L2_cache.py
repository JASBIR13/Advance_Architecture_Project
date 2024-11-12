import m5
from m5.objects import *
from decimal import Decimal, getcontext
import re

getcontext().prec = 10

# -------------------
# Cache Definitions
# -------------------

class L1Cache(Cache):
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

    def connectCPU(self, cpu):
        raise NotImplementedError("connectCPU must be implemented in subclasses.")

    def connectBus(self, bus):
        self.mem_side = bus.cpu_side_ports

class L1ICache(L1Cache):
    size = '32kB'

    def connectCPU(self, cpu):
        self.cpu_side = cpu.icache_port

class L1DCache(L1Cache):
    size = '128kB'

    def connectCPU(self, cpu):
        self.cpu_side = cpu.dcache_port

class L2Cache(Cache):
    size = '1MB'
    assoc = 8
    tag_latency = 10
    data_latency = 10
    response_latency = 10
    mshrs = 16
    tgts_per_mshr = 64

    def connectBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSide(self, bus):
        self.mem_side = bus.cpu_side_ports

# -------------------
# System Setup
# -------------------

def setup_system():
    system = System()

    # System Clock and Voltage Settings
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = "2GHz"
    system.clk_domain.voltage_domain = VoltageDomain(voltage="1.0V")

    # Memory and CPU Setup
    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange("1GB")]
    system.cpu = X86TimingSimpleCPU()

    # L1 Cache
    system.cpu.l1icache = L1ICache()
    system.cpu.l1icache.connectCPU(system.cpu)
    system.cpu.l1dcache = L1DCache()
    system.cpu.l1dcache.connectCPU(system.cpu)


    # L2 Cache
    system.l2cache = L2Cache()

    # Bus Connections
    system.l1bus = L2XBar()
    system.cpu.l1icache.connectBus(system.l1bus)
    system.cpu.l1dcache.connectBus(system.l1bus)
    system.l2cache.connectBus(system.l1bus)

    # Connect L2 to the Memory Bus
    system.membus = SystemXBar()
    system.l2cache.connectMemSide(system.membus)

    # Memory Controller
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

    # Set system port for CPU to access memory
    system.system_port = system.membus.cpu_side_ports

    # Interrupt Controller
    system.cpu.createInterruptController()
    system.cpu.interrupts[0].pio = system.membus.mem_side_ports
    system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports

    # Workload Configuration
    binary = 'tiled_matrix_multiply'
    system.workload = SEWorkload.init_compatible(binary)
    process = Process()
    process.cmd = [binary]
    system.cpu.workload = process
    system.cpu.createThreads()

    return system


def calculate_energy(stats):
        energy_factors = {
            'cpu_instruction': Decimal('0.001'),
            'icache_access': Decimal('0.006'),
            'icache_miss': Decimal('0.007'),
            'dcache_access': Decimal('0.007'),
            'dcache_miss': Decimal('0.008'),
            'l2_access': Decimal('0.008'),
            'l2_miss': Decimal('0.009'),
        }
        energy = Decimal('0.0')
        time_sec = stats.get('simSeconds', 0)

        # CPU Instructions
        insts = stats.get('system.cpu.commitStats0.numInsts', 0)
        energy += Decimal(insts) * energy_factors['cpu_instruction']


         # ICache Accesses and Misses
        icache_accesses = (
            stats.get('system.cpu.l1icache.demandAccesses::cpu.inst', 0) +
            stats.get('system.cpu.l1icache.demandAccesses::total', 0)
        )
        icache_misses = (
            stats.get('system.cpu.l1icache.demandMisses::cpu.inst', 0) +
            stats.get('system.cpu.l1icache.demandMisses::total', 0)
        )
        energy += Decimal(icache_accesses) * energy_factors['icache_access']
        energy += Decimal(icache_misses) * energy_factors['icache_miss']

        # DCache Accesses and Misses
        dcache_accesses = (
            stats.get('system.cpu.l1dcache.demandAccesses::cpu.data', 0) +
            stats.get('system.cpu.l1dcache.demandAccesses::total', 0)
        )
        dcache_misses = (
            stats.get('system.cpu.l1dcache.demandMisses::cpu.data', 0) +
            stats.get('system.cpu.l1dcache.demandMisses::total', 0)
        )
        energy += Decimal(dcache_accesses) * energy_factors['dcache_access']
        energy += Decimal(dcache_misses) * energy_factors['dcache_miss']

        # L2 Cache Accesses and Misses
        l2_accesses = (
            stats.get('system.l2cache.demandAccesses::cpu.inst', 0) +
            stats.get('system.l2cache.demandAccesses::cpu.data', 0)
        )
        l2_misses = (
            stats.get('system.l2cache.demandMisses::cpu.inst', 0) +
            stats.get('system.l2cache.demandMisses::cpu.data', 0)
        )
        energy += Decimal(l2_accesses) * energy_factors['l2_access']
        energy += Decimal(l2_misses) * energy_factors['l2_miss']

        # Convert pJ to nJ
        energy /= Decimal('1000.0')
        power = (energy * Decimal('1e-9')) / time_sec if time_sec > 0 else Decimal('0')
        print(f"Energy Consumed: {energy:.10f} nJ")
        print(f"Power Consumption: {power:.10f} W")

def parse_stats(stats_file_path='m5out/stats.txt'):
    stats = {}
    stat_list = [
        'simSeconds',
        'system.cpu.commitStats0.numInsts',
        'system.cpu.l1icache.demandAccesses::cpu.inst',
        'system.cpu.l1icache.demandAccesses::total',
        'system.cpu.l1icache.demandMisses::cpu.inst',
        'system.cpu.l1icache.demandMisses::total',
        'system.cpu.l1dcache.demandAccesses::cpu.data',
        'system.cpu.l1dcache.demandAccesses::total',
        'system.cpu.l1dcache.demandMisses::cpu.data',
        'system.cpu.l1dcache.demandMisses::total',
        'system.l2cache.demandAccesses::cpu.inst',
        'system.l2cache.demandAccesses::cpu.data',
        'system.l2cache.demandMisses::cpu.inst',
        'system.l2cache.demandMisses::cpu.data',
    ]

    # Read stats file
    with open(stats_file_path, 'r') as f:
        stats_output = f.read()

    # Updated regex to handle integers and floating points
    for stat in stat_list:
        pattern = re.compile(rf'^{re.escape(stat)}\s+([\d.eE+-]+)', re.MULTILINE)
        match = pattern.search(stats_output)
        if match:
            # Use Decimal to handle both integers and floats
            stats[stat] = Decimal(match.group(1))
        else:
            print(f"Warning: Stat '{stat}' not found in the stats file.")
            stats[stat] = Decimal('0.0')

    return stats

# -------------------
# Simulation Runner
# -------------------

def run_simulation():
    system = setup_system()
    root = Root(full_system=False, system=system)
    m5.instantiate()

    print("Starting simulation...")
    exit_event = m5.simulate()

    print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
    print("Dumping stats...")
    m5.stats.dump()
    stats = parse_stats('m5out/stats.txt')
    calculate_energy(stats)

    print("Simulation finished.")

# -------------------
# Main Execution
# -------------------
run_simulation()
