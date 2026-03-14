"""
Filecoin Storage Benchmark
Measures upload/retrieval throughput and deal latency on the Filecoin network
via the web3.storage / Storacha API (W3S) — the standard Filecoin data onramp.

Requirements:
    pip install -r requirements.txt
    export W3S_TOKEN="your_web3_storage_api_token"
"""

import os
import time
import json
import argparse
import hashlib
from datetime import datetime
from pathlib import Path

import requests

W3S_UPLOAD_URL = "https://up.web3.storage"
W3S_GATEWAY   = "https://w3s.link/ipfs"
RESULTS_DIR   = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_token() -> str:
    token = os.environ.get("W3S_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "W3S_TOKEN not set.\n"
            "Get a free token at https://web3.storage and run:\n"
            "  export W3S_TOKEN='your_token_here'"
        )
    return token


def generate_file(size_mb: float) -> bytes:
    return os.urandom(int(size_mb * 1024 * 1024))


def human_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} TB"


def human_speed(bps: float) -> str:
    return human_size(int(bps)) + "/s"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


# ── Upload ────────────────────────────────────────────────────────────────────

def benchmark_upload(data: bytes, label: str = "") -> dict:
    token = get_token()
    filename = f"bench_{sha256_hex(data)}.bin"
    print(f"  ↑  Uploading {human_size(len(data))}  [{label}]")

    start = time.perf_counter()
    resp = requests.post(
        f"{W3S_UPLOAD_URL}/upload",
        headers={
            "Authorization": f"Bearer {token}",
            "X-NAME": filename,
        },
        data=data,
        timeout=300,
    )
    elapsed = time.perf_counter() - start
    resp.raise_for_status()

    cid = resp.json().get("cid", resp.json().get("root", {}).get("/", "unknown"))
    throughput = len(data) / elapsed
    print(f"     ✓  CID: {cid}  |  {elapsed:.3f}s  |  {human_speed(throughput)}")

    return {
        "operation":       "upload",
        "label":           label,
        "filename":        filename,
        "size_bytes":      len(data),
        "size_human":      human_size(len(data)),
        "cid":             cid,
        "elapsed_sec":     round(elapsed, 4),
        "throughput_bps":  round(throughput, 2),
        "throughput_human":human_speed(throughput),
        "timestamp":       datetime.utcnow().isoformat(),
    }


# ── Retrieval ─────────────────────────────────────────────────────────────────

def benchmark_retrieve(cid: str, label: str = "") -> dict:
    url = f"{W3S_GATEWAY}/{cid}"
    print(f"  ↓  Retrieving {cid[:20]}...  [{label}]")

    start = time.perf_counter()
    resp = requests.get(url, timeout=300, stream=True)
    content = resp.content
    elapsed = time.perf_counter() - start
    resp.raise_for_status()

    throughput = len(content) / elapsed if elapsed > 0 else 0
    print(f"     ✓  {human_size(len(content))}  |  {elapsed:.3f}s  |  {human_speed(throughput)}")

    return {
        "operation":       "retrieve",
        "label":           label,
        "cid":             cid,
        "url":             url,
        "size_bytes":      len(content),
        "size_human":      human_size(len(content)),
        "elapsed_sec":     round(elapsed, 4),
        "throughput_bps":  round(throughput, 2),
        "throughput_human":human_speed(throughput),
        "timestamp":       datetime.utcnow().isoformat(),
    }


# ── Latency ───────────────────────────────────────────────────────────────────

def benchmark_latency(cid: str, repeat: int = 5) -> dict:
    url = f"{W3S_GATEWAY}/{cid}"
    print(f"  ⏱   Latency test  (×{repeat})  CID: {cid[:20]}...")
    latencies = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        requests.get(url, timeout=60).content
        latencies.append((time.perf_counter() - t0) * 1000)

    avg = sum(latencies) / len(latencies)
    print(f"     ✓  avg={avg:.1f}ms  min={min(latencies):.1f}ms  max={max(latencies):.1f}ms")

    return {
        "operation":   "latency",
        "cid":         cid,
        "repeat":      repeat,
        "latencies_ms":[round(l, 2) for l in latencies],
        "avg_ms":      round(avg, 2),
        "min_ms":      round(min(latencies), 2),
        "max_ms":      round(max(latencies), 2),
        "timestamp":   datetime.utcnow().isoformat(),
    }


# ── Full Suite ────────────────────────────────────────────────────────────────

def run_benchmark(sizes_mb: list, latency_repeat: int = 5) -> dict:
    print("\n" + "=" * 62)
    print("  Filecoin / web3.storage Benchmark")
    print("=" * 62)

    suite = {
        "meta": {
            "network":       "Filecoin (via web3.storage)",
            "gateway":       W3S_GATEWAY,
            "sizes_mb":      sizes_mb,
            "latency_repeat":latency_repeat,
            "run_at":        datetime.utcnow().isoformat(),
        },
        "uploads":   [],
        "retrievals":[],
        "latency":   None,
    }

    for size in sizes_mb:
        print(f"\n── {size} MB ──────────────────────────────────────────")
        data = generate_file(size)
        up   = benchmark_upload(data, label=f"{size}MB")
        suite["uploads"].append(up)
        ret  = benchmark_retrieve(up["cid"], label=f"{size}MB")
        suite["retrievals"].append(ret)

    last_cid = suite["uploads"][-1]["cid"]
    print(f"\n── Latency ────────────────────────────────────────────")
    suite["latency"] = benchmark_latency(last_cid, repeat=latency_repeat)

    ts       = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"benchmark_{ts}.json"
    out_path.write_text(json.dumps(suite, indent=2))

    print(f"\n✅  Results saved → {out_path}")
    print("=" * 62 + "\n")
    return suite


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filecoin Storage Benchmark via web3.storage"
    )
    parser.add_argument(
        "--sizes", nargs="+", type=float, default=[0.5, 1.0, 5.0],
        help="File sizes in MB (default: 0.5 1 5)",
    )
    parser.add_argument(
        "--latency-repeat", type=int, default=5,
        help="Latency test repetitions (default: 5)",
    )
    args = parser.parse_args()
    run_benchmark(sizes_mb=args.sizes, latency_repeat=args.latency_repeat)
