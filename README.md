# Filecoin Storage Benchmark

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Filecoin](https://img.shields.io/badge/Filecoin-web3.storage-0090FF?style=flat&logo=filecoin&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-00d8a4?style=flat)
![CI](https://img.shields.io/github/actions/workflow/status/hosammahdy91/filecoin-storage-benchmark/ci.yml?label=CI&style=flat)

Benchmarking and stress testing tools for the **Filecoin** decentralized storage network via the [web3.storage](https://web3.storage) API.

---

## Overview

This project provides experimental benchmarking tools to evaluate Filecoin storage performance:

| Feature | Description |
|---|---|
| Upload throughput | Measures speed & latency to store data on Filecoin via web3.storage |
| Retrieval latency | Tests data retrieval speed through the w3s.link gateway |
| Concurrent stress | Simulates parallel workers to measure performance under load |
| Result visualization | Auto-generates Matplotlib charts from JSON result files |

The goal is to explore how Filecoin performs for real-world workloads such as AI dataset hosting, media distribution, and decentralized application storage.

---

## Repository Structure

```
filecoin-storage-benchmark/
│
├── benchmark/
│   ├── benchmark.py        # Upload / retrieval / latency benchmark
│   └── stress_test.py      # Concurrent stress test
│
├── dashboard/
│   └── plot_results.py     # Matplotlib chart generator
│
├── results/                # JSON output files (auto-created)
│   └── README.md
│
├── .github/
│   └── workflows/
│       └── ci.yml          # Lint & import checks
│
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A free [web3.storage](https://web3.storage) account and API token

### 2. Clone this repository

```bash
git clone https://github.com/hosammahdy91/filecoin-storage-benchmark.git
cd filecoin-storage-benchmark
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API token

```bash
export W3S_TOKEN="your_web3_storage_token_here"
```

### 5. Run the benchmark

```bash
# Default: tests 0.5 MB, 1 MB, 5 MB files
python benchmark/benchmark.py

# Custom file sizes
python benchmark/benchmark.py --sizes 1 10 50

# More latency repetitions
python benchmark/benchmark.py --sizes 1 5 --latency-repeat 10
```

### 6. Run the stress test

```bash
# Default: 8 workers, 256 KB per file
python benchmark/stress_test.py

# Custom
python benchmark/stress_test.py --workers 16 --file-size-kb 512
```

### 7. Visualize results

```bash
# Benchmark chart
python dashboard/plot_results.py --type benchmark

# Stress test chart
python dashboard/plot_results.py --type stress
```

Charts are saved to `dashboard/benchmark_chart.png` and `dashboard/stress_chart.png`.

---

## Example Output

```
══════════════════════════════════════════════════════════════
  Filecoin / web3.storage Benchmark
══════════════════════════════════════════════════════════════

── 1.0 MB ───────────────────────────────────────────────────
  ↑  Uploading 1.00 MB  [1.0MB]
     ✓  CID: bafybeig...  |  1.243s  |  824.36 KB/s
  ↓  Retrieving bafybeig...  [1.0MB]
     ✓  1.00 MB  |  0.412s  |  2.43 MB/s

── Latency ──────────────────────────────────────────────────
  ⏱   Latency test  (×5)
     ✓  avg=398.2ms  min=341.1ms  max=471.6ms

✅  Results saved → results/benchmark_20250314_153201.json
══════════════════════════════════════════════════════════════
```

---

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `--sizes` | `0.5 1 5` | File sizes in MB |
| `--latency-repeat` | `5` | Latency test repetitions |
| `--workers` | `8` | Concurrent workers |
| `--file-size-kb` | `256` | KB per worker file |

---

## Example Use Cases

- AI dataset storage benchmarking
- Large media file distribution
- NFT asset and metadata storage
- Decentralized app (dApp) data hosting
- Comparing Filecoin vs centralized cloud storage

---

## License

MIT © [Hosam](https://github.com/hosammahdy91)
