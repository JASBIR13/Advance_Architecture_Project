import m5
from m5.objects import *
from decimal import Decimal, getcontext
import re

getcontext().prec = 10

# -------------------
# Cache Definitions
# -------------------

class L0Cache(Cache):
    assoc = 1
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 4
    tgts_per_mshr = 30

    def connectCPU(self, cpu):
        raise NotImplementedError("connectCPU must be implemented in subclasses.")

    def connectBus(self, bus):
        self.mem_side = bus.cpu_side_ports

class L0ICache(L0Cache):
    size = '16kB'

    def connectCPU(self, cpu):
        self.cpu_side = cpu.icache_port

class L0DCache(L0Cache):
    size = '64kB'

    def connectCPU(self, cpu):
        self.cpu_side = cpu.dcache_port

class L1Cache(Cache):
    size = '256kB'
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSideBus(self, bus):
        self.mem_side = bus.cpu_side_ports

class L2HighFreqCache(Cache):
    size = '512kB'
    assoc = 4
    tag_latency = 5
    data_latency = 5
    response_latency = 5
    mshrs = 8
    tgts_per_mshr = 32

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.addr_ranges = [AddrRange(start=0x00000000, size='512MB')]

class L2LowFreqCache(Cache):
    size = '1MB'
    assoc = 8
    tag_latency = 10
    data_latency = 10
    response_latency = 10
    mshrs = 16
    tgts_per_mshr = 64

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.addr_ranges = [AddrRange(start=0x20000000, size='512MB')]

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

    # L0 Cache (Instruction and Data)
    system.cpu.icache = L0ICache()
    system.cpu.dcache = L0DCache()
    system.cpu.icache.connectCPU(system.cpu)
    system.cpu.dcache.connectCPU(system.cpu)

    # Bus for L1
    system.l1bus = L2XBar()
    system.cpu.icache.connectBus(system.l1bus)
    system.cpu.dcache.connectBus(system.l1bus)

    # L1 Cache
    system.l1cache = L1Cache()
    system.l1cache.connectCPUSideBus(system.l1bus)

    # Separate L2 Cache Banks
    system.l2highfreq = L2HighFreqCache()
    system.l2lowfreq = L2LowFreqCache()

    # Bus for L2 Banks
    system.l2bus = L2XBar()
    system.l1cache.connectMemSideBus(system.l2bus)

    # Connect L2 caches to L2 bus
    system.l2highfreq.cpu_side = system.l2bus.mem_side_ports
    system.l2lowfreq.cpu_side = system.l2bus.mem_side_ports

    # Memory Bus and Controller
    system.membus = SystemXBar()
    system.l2highfreq.mem_side = system.membus.cpu_side_ports
    system.l2lowfreq.mem_side = system.membus.cpu_side_ports
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports
    system.system_port = system.membus.cpu_side_ports

    # Interrupts
    system.cpu.createInterruptController()
    system.cpu.interrupts[0].pio = system.membus.mem_side_ports
    system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports

    # Workload
    binary = 'tiled_matrix_multiply'
    system.workload = SEWorkload.init_compatible(binary)
    process = Process()
    process.cmd = [binary]
    system.cpu.workload = process
    system.cpu.createThreads()

    return system

# -------------------
# Power Model
# -------------------

def calculate_energy(stats):
        energy_factors = {
            'cpu_instruction': Decimal('0.001'),
            'icache_access': Decimal('0.002'),
            'icache_miss': Decimal('0.003'),
            'dcache_access': Decimal('0.004'),
            'dcache_miss': Decimal('0.005'),
            'l1_access': Decimal('0.006'),
            'l1_miss': Decimal('0.007'),
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
            stats.get('system.cpu.icache.demandAccesses::cpu.inst', 0) +
            stats.get('system.cpu.icache.demandAccesses::total', 0)
        )
        icache_misses = (
            stats.get('system.cpu.icache.demandMisses::cpu.inst', 0) +
            stats.get('system.cpu.icache.demandMisses::total', 0)
        )
        energy += Decimal(icache_accesses) * energy_factors['icache_access']
        energy += Decimal(icache_misses) * energy_factors['icache_miss']

        # DCache Accesses and Misses
        dcache_accesses = (
            stats.get('system.cpu.dcache.demandAccesses::cpu.data', 0) +
            stats.get('system.cpu.dcache.demandAccesses::total', 0)
        )
        dcache_misses = (
            stats.get('system.cpu.dcache.demandMisses::cpu.data', 0) +
            stats.get('system.cpu.dcache.demandMisses::total', 0)
        )
        energy += Decimal(dcache_accesses) * energy_factors['dcache_access']
        energy += Decimal(dcache_misses) * energy_factors['dcache_miss']

        # L1 Cache Accesses and Misses
        l1_accesses = (
            stats.get('system.l1cache.demandAccesses::cpu.inst', 0) +
            stats.get('system.l1cache.demandAccesses::cpu.data', 0)
        )
        l1_misses = (
            stats.get('system.l1cache.demandMisses::cpu.inst', 0) +
            stats.get('system.l1cache.demandMisses::cpu.data', 0)
        )
        energy += Decimal(l1_accesses) * energy_factors['l1_access']
        energy += Decimal(l1_misses) * energy_factors['l1_miss']

        # L2 Cache Accesses and Misses
        l2_accesses = (
            stats.get('system.l2highfreq.demandAccesses::cpu.inst', 0) +
            stats.get('system.l2highfreq.demandAccesses::cpu.data', 0)
        )
        l2_misses = (
            stats.get('system.l2highfreq.demandMisses::cpu.inst', 0) +
            stats.get('system.l2highfreq.demandMisses::cpu.data', 0)
        )
        energy += Decimal(l2_accesses) * energy_factors['l2_access']
        energy += Decimal(l2_misses) * energy_factors['l2_miss']

        # Convert pJ to nJ
        energy /= Decimal('1000.0')
        power = (energy * Decimal('1e-9')) / time_sec if time_sec > 0 else Decimal('0')
        print(f"Energy Consumed: {energy:.10f} nJ")
        print(f"Power Consumption: {power:.10f} W")


# -------------------
# Statistics Parsing
# -------------------

def parse_stats(stats_file_path='m5out/stats.txt'):
    stats = {}
    stat_list = [
        'simSeconds',
        'system.cpu.commitStats0.numInsts',
        'system.cpu.icache.demandAccesses::cpu.inst',
        'system.cpu.icache.demandAccesses::total',
        'system.cpu.icache.demandMisses::cpu.inst',
        'system.cpu.icache.demandMisses::total',
        'system.cpu.dcache.demandAccesses::cpu.data',
        'system.cpu.dcache.demandAccesses::total',
        'system.cpu.dcache.demandMisses::cpu.data',
        'system.cpu.dcache.demandMisses::total',
        'system.l1cache.demandAccesses::cpu.inst',
        'system.l1cache.demandAccesses::cpu.data',
        'system.l1cache.demandMisses::cpu.inst',
        'system.l1cache.demandMisses::cpu.data',
        'system.l2highfreq.demandAccesses::cpu.inst',
        'system.l2highfreq.demandAccesses::cpu.data',
        'system.l2highfreq.demandMisses::cpu.inst',
        'system.l2highfreq.demandMisses::cpu.data',
    ]

    with open(stats_file_path, 'r') as f:
        stats_output = f.read()

    for stat in stat_list:
        pattern = re.compile(rf'^{re.escape(stat)}\s+([\d.eE+-]+)', re.MULTILINE)
        match = pattern.search(stats_output)
        if match:
            stats[stat] = Decimal(match.group(1))
        else:
            print(f"Warning: Stat '{stat}' not found in the stats file.")
            stats[stat] = Decimal('0.0')

    return stats


# -------------------
# Simulation Runner
# -------------------

def run_simulation(num_intervals=100):
    system = setup_system()

    
    dvfs_levels = [
        ("1.5GHz", "0.8V"),
        ("2.0GHz", "1.0V"),
        ("2.5GHz", "1.2V")
    ]
    # Set root and instantiate the system
    root = Root(full_system=False, system=system)
    m5.instantiate()

    ticks_per_interval = 100000000 

    # Initialize clock frequency and voltage
    current_freq, current_volt = dvfs_levels[0]
    system.clk_domain.clock = current_freq
    system.clk_domain.voltage_domain.voltage = current_volt

    print(f"Starting simulation with initial frequency {current_freq} and voltage {current_volt}")

    for i in range(num_intervals):
        freq, volt = dvfs_levels[i % len(dvfs_levels)]  # Cycle through DVFS levels
        print(f"\n--- Interval {i + 1} ---")
        print(f"Setting frequency to {freq} and voltage to {volt}")

        system.clk_domain.clock = freq
        system.clk_domain.voltage_domain.voltage = volt


        exit_event = m5.simulate(ticks_per_interval)

        print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
        

        if exit_event.getCause() == "exiting with last active thread context":
            m5.stats.dump()
            stats = parse_stats('m5out/stats.txt')
            calculate_energy(stats)
            print("Workload has completed; ending simulation.")
            break


# -------------------
# Main Execution
# -------------------
run_simulation()