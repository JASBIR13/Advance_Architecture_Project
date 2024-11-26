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
