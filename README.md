
# Advance_Architecture_Project

### Prerequisites

* Ensure that `gem5` is installed and built on your system.

### Setup Instructions

#### Step 1: Clone the Repository

Clone this project **outside** the `gem5` directory. Use the following command to clone the repository:

```bash
git clone <repository-url>
```

#### Step 2: Modify Workloads in Cache Files

You can change the workload in both `our_cache.py` and `basicL1L2_cache.py` by modifying the binary:

```python
binary = 'tiled_convolution'
```

Replace `'tiled_convolution'` with the path to your desired workload binary.

#### Step 3: Run the Cache Files

Execute the cache configuration files using the following commands:

```bash
./gem5/build/X86/gem5.opt basicL1L2_cache.py

OR

./gem5/build/X86/gem5.opt our_cache.py
```



### Energy Calculation Example: L0 Cache (16KB, Associativity 1)

Below is an example of the part of output in format for energy calculations with an **L0 cache** of size **16KB** and associativity  **1** :

```bash
Access time (ns):                       0.775842
Cycle time (ns):                        0.827019
Total dynamic read energy per access (nJ): 0.106922
Total dynamic write energy per access (nJ): 0.196762
Total leakage power of a bank (mW):     8.34532
Total gate leakage power of a bank (mW): 0.724312
Cache height x width (mm):              0.567078 x 0.748468
```



### Cache.cfg is a sample file we have used to calculate energy of L0 cache and can only be run when you have full CACTI repository
