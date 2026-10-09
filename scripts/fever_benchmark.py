"""FEVER benchmark for rag-audit. Dev split picks the threshold; test split is run once after.

Task: a claim cited to its gold evidence. SUPPORTS -> auditor should say SUPPORTED;
REFUTES and NOT ENOUGH INFO -> auditor should flag it (positive class = flagged).

Usage:
  python scripts/fever_benchmark.py dev     # score dev items, sweep, write results/frozen.json
  python scripts/fever_benchmark.py test    # refuses to run without frozen.json; runs once
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from datasets import load_dataset

from rag_audit import FactualityAuditor, Verdict
from rag_audit.auditor import passages
from rag_audit.nli import CrossEncoderNLI

OUT = Path("results")
PER_LABEL = 600
LABELS = ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO")


def sample(split: str, seed: int) -> list[dict[str, str]]:
    ds = load_dataset("copenlu/fever_gold_evidence", split=split)
    rng = random.Random(seed)
    items: list[dict[str, str]] = []
    for label in LABELS:
        idx = [i for i, lb in enumerate(ds["label"]) if lb == label]
        for i in rng.sample(idx, PER_LABEL):
            row = ds[i]
            text = " ".join(e[2] for e in row["evidence"] if e[2])
            claim = row["claim"].strip()
            if text and claim:
                items.append({"id": row["id"], "label": label, "claim": claim, "evidence": text})
    return items


def score_items(items: list[dict[str, str]], scorer: CrossEncoderNLI) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for k, it in enumerate(items):
        t = time.perf_counter()
        best_e = best_c = 0.0
        for _, _, p in passages(it["evidence"]):
            s = scorer.score(p, it["claim"])
            best_e, best_c = max(best_e, s.entailment), max(best_c, s.contradiction)
        rows.append({**it, "ent": best_e, "con": best_c, "sec": time.perf_counter() - t})
        if k % 200 == 0:
            print(f"  {k}/{len(items)}  {time.perf_counter() - t0:.0f}s", flush=True)
    return rows


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (conf >= lo) & (conf <= hi if hi == 1 else conf < hi)
        if m.any():
            total += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(total)


def prf(flag: np.ndarray, positive: np.ndarray) -> tuple[float, float, float]:
    tp = float((flag & positive).sum())
    p = tp / flag.sum() if flag.sum() else 0.0
    r = tp / positive.sum() if positive.sum() else 0.0
    return float(p), float(r), float(2 * p * r / (p + r) if p + r else 0.0)


def main() -> None:
    mode = sys.argv[1]
    OUT.mkdir(exist_ok=True)
    scorer = CrossEncoderNLI()
    if mode == "dev":
        rows = score_items(sample("validation", seed=0), scorer)
        (OUT / "dev_scores.json").write_text(json.dumps(rows))
        ent = np.array([r["ent"] for r in rows], dtype=float)
        positive = np.array([r["label"] != "SUPPORTS" for r in rows])
        sweep = []
        for thr in np.round(np.arange(0.05, 1.0, 0.05), 2):
            p, r, f = prf(ent < thr, positive)
            sweep.append({"threshold": float(thr), "precision": p, "recall": r, "f1": f})
        best = max(sweep, key=lambda s: s["f1"])
        (OUT / "dev_sweep.json").write_text(json.dumps(sweep, indent=1))
        (OUT / "frozen.json").write_text(json.dumps({"entail_threshold": best["threshold"], "dev_f1": best["f1"]}))
        print("frozen:", best)
        return
    frozen = json.loads((OUT / "frozen.json").read_text())
    if (OUT / "test_scores.json").exists():
        sys.exit("test already run once; refusing to re-run (delete results/test_scores.json deliberately)")
    thr = float(frozen["entail_threshold"])
    items = sample("test", seed=2)
    auditor = FactualityAuditor(scorer, entail_threshold=thr)
    trows: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for k, it in enumerate(items):
        t = time.perf_counter()
        rep = auditor.audit([it["evidence"]], it["claim"].rstrip(".") + ". [1]")
        res = rep.results[0]
        trows.append({**it, "verdict": res.verdict.value, "sec": time.perf_counter() - t,
                     "ent": res.best_evidence.scores.entailment if res.best_evidence else 0.0})
        if k % 200 == 0:
            print(f"  {k}/{len(items)}  {time.perf_counter() - t0:.0f}s", flush=True)
    (OUT / "test_scores.json").write_text(json.dumps(trows))
    labels = np.array([r["label"] for r in trows])
    flag = np.array([r["verdict"] != Verdict.SUPPORTED.value for r in trows])
    positive = labels != "SUPPORTS"
    p, rec, f1 = prf(flag, positive)
    ent = np.array([r["ent"] for r in trows], dtype=float)
    summary = {
        "n": len(trows), "threshold": thr, "precision": p, "recall": rec, "f1": f1,
        "recall_refutes": float(flag[labels == "REFUTES"].mean()),
        "recall_nei": float(flag[labels == "NOT ENOUGH INFO"].mean()),
        "supports_kept": float((~flag[labels == "SUPPORTS"]).mean()),
        "contradicted_share_of_refutes": float(np.mean([r["verdict"] == "CONTRADICTED" for r in trows if r["label"] == "REFUTES"])),
        "ece_ent_as_p_supports": ece(np.clip(ent, 0, 1), (~positive).astype(float)),
        "latency_p50_s": float(np.median([r["sec"] for r in trows])),
        "latency_p95_s": float(np.percentile([r["sec"] for r in trows], 95)),
    }
    (OUT / "test_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
