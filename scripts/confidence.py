"""95% confidence intervals (Wilson) for accuracy results, because small test sets are noisy.

Usage (from the project folder):
    python scripts\\confidence.py 240 240 "Rules reader, 30 synthetic offers (fields)"
    python scripts\\confidence.py 60 64 "Rules reader, 8 hard offers (fields)"
Arguments: number correct, number total, and an optional label.
"""
import math
import sys


def wilson(correct, total, z=1.96):
    """Range that probably contains the true accuracy. Works well even at 100% or with few cases."""
    if total <= 0:
        raise ValueError("total must be above 0")
    if not 0 <= correct <= total:
        raise ValueError("correct must be between 0 and total")
    p = correct / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return
    correct, total = int(argv[1]), int(argv[2])
    label = argv[3] if len(argv) > 3 else ""
    p, lo, hi = wilson(correct, total)
    print(f"{label}: {correct}/{total} = {p * 100:.1f}%  (95% CI {lo * 100:.1f}% to {hi * 100:.1f}%)")


if __name__ == "__main__":
    main(sys.argv)
