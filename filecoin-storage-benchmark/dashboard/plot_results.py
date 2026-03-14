"""
Filecoin Benchmark Dashboard
Reads the latest JSON result from results/ and generates
publication-quality charts with a dark Filecoin-themed palette.

Usage:
    python dashboard/plot_results.py --type benchmark
    python dashboard/plot_results.py --type stress
"""

import json
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

RESULTS_DIR   = Path(__file__).parent.parent / "results"
DASHBOARD_DIR = Path(__file__).parent

# ── Filecoin dark palette ─────────────────────────────────────────────────────
BG      = "#0d1117"
SURFACE = "#161b22"
CARD    = "#21262d"
BORDER  = "#30363d"
BLUE    = "#0090ff"
TEAL    = "#00d8a4"
AMBER   = "#f0a500"
RED     = "#f85149"
TEXT    = "#e6edf3"
MUTED   = "#7d8590"


def _style_ax(ax):
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.grid(True, color=BORDER, alpha=0.5, linewidth=0.5)


def load_latest(prefix: str) -> dict:
    files = sorted(RESULTS_DIR.glob(f"{prefix}_*.json"))
    if not files:
        raise FileNotFoundError(
            f"No '{prefix}_*.json' files found in {RESULTS_DIR}.\n"
            "Run the benchmark first:\n"
            f"  python benchmark/{prefix}.py"
        )
    path = files[-1]
    print(f"  Loading: {path.name}")
    return json.loads(path.read_text())


# ── Benchmark charts ──────────────────────────────────────────────────────────

def plot_benchmark(data: dict, out_path: Path):
    uploads   = data["uploads"]
    retrievals = data["retrievals"]
    latency   = data.get("latency", {})

    sizes       = [u["size_human"] for u in uploads]
    up_tp       = [u["throughput_bps"] / 1_048_576 for u in uploads]    # MB/s
    ret_tp      = [r["throughput_bps"] / 1_048_576 for r in retrievals]
    up_elapsed  = [u["elapsed_sec"] for u in uploads]
    ret_elapsed = [r["elapsed_sec"] for r in retrievals]
    lats        = latency.get("latencies_ms", [])

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.patch.set_facecolor(BG)
    fig.suptitle("Filecoin Storage Benchmark Results", fontsize=15,
                 fontweight="bold", color=TEXT, y=1.01)

    for ax in axes.flat:
        _style_ax(ax)

    x = np.arange(len(sizes))
    w = 0.36

    # ── 1. Throughput bar chart ──
    ax = axes[0, 0]
    ax.bar(x - w / 2, up_tp,  w, label="Upload",   color=BLUE, alpha=0.88)
    ax.bar(x + w / 2, ret_tp, w, label="Retrieval", color=TEAL, alpha=0.88)
    ax.set_title("Throughput (MB/s)")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.set_xlabel("File Size")
    ax.set_ylabel("MB/s")
    ax.legend(facecolor=CARD, labelcolor=TEXT, edgecolor=BORDER, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    # ── 2. Elapsed time line ──
    ax = axes[0, 1]
    ax.plot(sizes, up_elapsed,  "o-", color=BLUE, label="Upload",   lw=2, ms=7)
    ax.plot(sizes, ret_elapsed, "s-", color=TEAL, label="Retrieval", lw=2, ms=7)
    ax.set_title("Elapsed Time (seconds)")
    ax.set_xlabel("File Size")
    ax.set_ylabel("Seconds")
    ax.legend(facecolor=CARD, labelcolor=TEXT, edgecolor=BORDER, fontsize=9)

    # ── 3. Latency bar + mean line ──
    ax = axes[1, 0]
    if lats:
        xs  = list(range(len(lats)))
        avg = sum(lats) / len(lats)
        ax.bar(xs, lats, color=AMBER, alpha=0.85, zorder=3)
        ax.axhline(avg, color=RED, lw=1.5, ls="--",
                   label=f"avg = {avg:.1f} ms", zorder=4)
        ax.set_title("Retrieval Latency per Request (ms)")
        ax.set_xlabel("Request #")
        ax.set_ylabel("ms")
        ax.legend(facecolor=CARD, labelcolor=TEXT, edgecolor=BORDER, fontsize=9)
    else:
        ax.text(0.5, 0.5, "No latency data", ha="center", va="center",
                color=MUTED, transform=ax.transAxes)
        ax.set_title("Latency")

    # ── 4. Summary table ──
    ax = axes[1, 1]
    ax.axis("off")
    rows = []
    for u, r in zip(uploads, retrievals):
        rows.append([
            u["size_human"],
            f"{u['throughput_bps']/1024:.1f} KB/s",
            f"{r['throughput_bps']/1024:.1f} KB/s",
            f"{latency.get('avg_ms', '—')} ms",
        ])
    tbl = ax.table(
        cellText=rows,
        colLabels=["Size", "Upload Speed", "Retrieval Speed", "Avg Latency"],
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.7)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_facecolor(CARD if row > 0 else BORDER)
        cell.set_text_props(color=TEXT)
        cell.set_edgecolor(BORDER)
    ax.set_title("Summary", color=TEXT)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  ✅  Chart saved → {out_path}")


# ── Stress charts ─────────────────────────────────────────────────────────────

def plot_stress(data: dict, out_path: Path):
    up_ok  = [r for r in data["upload_results"]   if r["status"] == "success"]
    ret_ok = [r for r in data["retrieve_results"] if r["status"] == "success"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        f"Filecoin Stress Test  |  {data['meta']['workers']} workers  "
        f"|  {data['meta']['file_size_kb']} KB/file",
        fontsize=14, fontweight="bold", color=TEXT,
    )
    for ax in axes:
        _style_ax(ax)

    # Upload elapsed per worker
    ax = axes[0]
    wids = [r["worker_id"] for r in up_ok]
    elt  = [r["elapsed_sec"] for r in up_ok]
    ax.bar(wids, elt, color=BLUE, alpha=0.88)
    ax.set_title("Upload Time per Worker (s)", color=TEXT)
    ax.set_xlabel("Worker ID")
    ax.set_ylabel("Seconds")

    # Retrieval elapsed per worker
    ax = axes[1]
    wids2 = [r["worker_id"] for r in ret_ok]
    elt2  = [r["elapsed_sec"] for r in ret_ok]
    ax.bar(wids2, elt2, color=TEAL, alpha=0.88)
    ax.set_title("Retrieval Time per Worker (s)", color=TEXT)
    ax.set_xlabel("Worker ID")
    ax.set_ylabel("Seconds")

    # Throughput scatter
    ax = axes[2]
    up_tp  = [r["throughput_bps"] / 1024 for r in up_ok]
    ret_tp = [r["throughput_bps"] / 1024 for r in ret_ok]
    ax.scatter(range(len(up_tp)),  up_tp,  color=BLUE, label="Upload",    s=60, zorder=3)
    ax.scatter(range(len(ret_tp)), ret_tp, color=TEAL, label="Retrieval", s=60, zorder=3, marker="s")
    ax.set_title("Throughput per Worker (KB/s)", color=TEXT)
    ax.set_xlabel("Worker #")
    ax.set_ylabel("KB/s")
    ax.legend(facecolor=CARD, labelcolor=TEXT, edgecolor=BORDER, fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  ✅  Stress chart saved → {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot Filecoin benchmark results")
    parser.add_argument(
        "--type", choices=["benchmark", "stress"], default="benchmark",
        help="Which result file to plot",
    )
    args = parser.parse_args()

    print("\n📊  Filecoin Benchmark Dashboard")
    print("=" * 42)
    data = load_latest(prefix=args.type)
    out  = DASHBOARD_DIR / f"{args.type}_chart.png"

    if args.type == "benchmark":
        plot_benchmark(data, out)
    else:
        plot_stress(data, out)
