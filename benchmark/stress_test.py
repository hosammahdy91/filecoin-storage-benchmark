"""
Filecoin Concurrent Stress Test
Runs parallel upload + retrieval workers against web3.storage
and reports per-worker timing, throughput, and success rate.
"""

import os
import time
import json
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

W3S_UPLOAD_URL = "https://up.web3.storage"
W3S_GATEWAY    = "https://w3s.link/ipfs"
RESULTS_DIR    = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def get_token() -> str:
    token = os.environ.get("W3S_TOKEN", "")
    if not token:
        raise EnvironmentError("W3S_TOKEN not set. See README for instructions.")
    return token


def upload_worker(worker_id: int, size_bytes: int) -> dict:
    data  = os.urandom(size_bytes)
    token = get_token()
    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{W3S_UPLOAD_URL}/upload",
            headers={"Authorization": f"Bearer {token}", "X-NAME": f"stress_{worker_id}.bin"},
            data=data,
            timeout=300,
        )
        elapsed = time.perf_counter() - start
        resp.raise_for_status()
        cid = resp.json().get("cid", "unknown")
        throughput = size_bytes / elapsed
        print(f"  [{worker_id:02d}] ↑  {elapsed:.3f}s  {throughput/1024:.1f} KB/s  {cid[:18]}...")
        return {"worker_id": worker_id, "status": "success", "cid": cid,
                "size_bytes": size_bytes, "elapsed_sec": round(elapsed, 4),
                "throughput_bps": round(throughput, 2)}
    except Exception as exc:
        elapsed = time.perf_counter() - start
        print(f"  [{worker_id:02d}] ✗  {exc}")
        return {"worker_id": worker_id, "status": "error", "error": str(exc),
                "elapsed_sec": round(elapsed, 4)}


def retrieve_worker(worker_id: int, cid: str) -> dict:
    url   = f"{W3S_GATEWAY}/{cid}"
    start = time.perf_counter()
    try:
        content  = requests.get(url, timeout=300).content
        elapsed  = time.perf_counter() - start
        throughput = len(content) / elapsed if elapsed > 0 else 0
        print(f"  [{worker_id:02d}] ↓  {elapsed:.3f}s  {throughput/1024:.1f} KB/s")
        return {"worker_id": worker_id, "status": "success", "cid": cid,
                "size_bytes": len(content), "elapsed_sec": round(elapsed, 4),
                "throughput_bps": round(throughput, 2)}
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return {"worker_id": worker_id, "status": "error", "error": str(exc),
                "elapsed_sec": round(elapsed, 4)}


def summarize(results: list, label: str) -> dict:
    ok     = [r for r in results if r["status"] == "success"]
    failed = len(results) - len(ok)
    if not ok:
        return {"label": label, "total": len(results), "success": 0, "failed": failed}
    elaps  = [r["elapsed_sec"] for r in ok]
    tput   = [r["throughput_bps"] for r in ok]
    return {
        "label":            label,
        "total":            len(results),
        "success":          len(ok),
        "failed":           failed,
        "success_rate_pct": round(len(ok) / len(results) * 100, 1),
        "avg_elapsed_sec":  round(sum(elaps) / len(elaps), 4),
        "min_elapsed_sec":  round(min(elaps), 4),
        "max_elapsed_sec":  round(max(elaps), 4),
        "avg_throughput_bps": round(sum(tput) / len(tput), 2),
    }


def run_stress(workers: int = 8, file_size_kb: int = 256) -> dict:
    size_bytes = file_size_kb * 1024
    print("\n" + "=" * 62)
    print(f"  Filecoin Stress Test  |  {workers} workers  |  {file_size_kb} KB/file")
    print("=" * 62)

    # Phase 1 — concurrent uploads
    print(f"\n[Phase 1]  Concurrent Uploads  ({workers} workers)")
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(upload_worker, i, size_bytes) for i in range(workers)]
        upload_results = [f.result() for f in as_completed(futs)]
    upload_wall = round(time.perf_counter() - t0, 4)

    successful_cids = [r["cid"] for r in upload_results if r.get("cid") and r["status"] == "success"]

    # Phase 2 — concurrent retrievals
    print(f"\n[Phase 2]  Concurrent Retrievals  ({len(successful_cids)} files)")
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(retrieve_worker, i, cid) for i, cid in enumerate(successful_cids)]
        retrieve_results = [f.result() for f in as_completed(futs)]
    retrieve_wall = round(time.perf_counter() - t0, 4)

    up_summary  = summarize(upload_results,   "uploads")
    ret_summary = summarize(retrieve_results, "retrievals")

    print(f"\n{'─'*62}")
    print(f"  Uploads    → {up_summary['success']}/{up_summary['total']} OK  "
          f"wall={upload_wall}s  avg={up_summary.get('avg_elapsed_sec', '—')}s/file")
    print(f"  Retrievals → {ret_summary['success']}/{ret_summary['total']} OK  "
          f"wall={retrieve_wall}s  avg={ret_summary.get('avg_elapsed_sec', '—')}s/file")
    print(f"{'─'*62}\n")

    suite = {
        "meta": {
            "network":      "Filecoin (via web3.storage)",
            "workers":      workers,
            "file_size_kb": file_size_kb,
            "run_at":       datetime.utcnow().isoformat(),
        },
        "upload_wall_sec":   upload_wall,
        "retrieve_wall_sec": retrieve_wall,
        "upload_summary":    up_summary,
        "retrieve_summary":  ret_summary,
        "upload_results":    upload_results,
        "retrieve_results":  retrieve_results,
    }

    ts       = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"stress_{ts}.json"
    out_path.write_text(json.dumps(suite, indent=2))
    print(f"✅  Results saved → {out_path}\n")
    return suite


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filecoin Concurrent Stress Test")
    parser.add_argument("--workers",      type=int, default=8,   help="Parallel workers (default: 8)")
    parser.add_argument("--file-size-kb", type=int, default=256, help="KB per worker (default: 256)")
    args = parser.parse_args()
    run_stress(workers=args.workers, file_size_kb=args.file_size_kb)
