#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GOLDEN_PATH = Path(__file__).resolve().parent / "golden_set.json"


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def post_chat(
    base_url: str,
    question: str,
    rerank: bool,
    timeout: float,
    hybrid: bool = False,
    token: str = "",
) -> dict:
    body = json.dumps(
        {
            "question": question,
            "rerank": rerank,
            "hybrid": hybrid,
            "retrieve_only": True,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"{base_url.rstrip('/')}/chat",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"/chat trả HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Không kết nối được {base_url}. Hãy khởi động stack trước."
        ) from exc


def source_names(payload: object) -> list[str]:
    if not isinstance(payload, list):
        return []
    names: list[str] = []
    for item in payload:
        name = item.get("source") if isinstance(item, dict) else item
        if isinstance(name, str):
            names.append(name)
    return names


def evaluate(
    items: list[dict],
    base_url: str,
    rerank: bool,
    timeout: float,
    hybrid: bool = False,
    token: str = "",
) -> dict:
    latencies: list[float] = []
    recall_hits = 0
    recall_total = 0
    reciprocal_ranks: list[float] = []
    trap_total = 0
    trap_refused = 0
    attack_total = 0
    attack_blocked = 0
    real_total = 0
    real_blocked = 0

    for item in items:
        expected = set(item.get("expect", []))
        started = time.perf_counter()
        payload = post_chat(base_url, item["q"], rerank, timeout, hybrid, token)
        latencies.append(time.perf_counter() - started)

        candidates = source_names(payload.get("retrieved_sources", payload.get("sources")))
        final_sources = source_names(payload.get("sources"))
        if expected:
            real_total += 1
            real_blocked += int(bool(payload.get("blocked")))
            recall_total += 1
            recall_hits += int(bool(expected.intersection(candidates)))
            rank = next(
                (index for index, source in enumerate(final_sources, start=1) if source in expected),
                None,
            )
            reciprocal_ranks.append(1 / rank if rank else 0.0)
        elif item.get("attack"):
            attack_total += 1
            attack_blocked += int(bool(payload.get("blocked")))
        else:
            trap_total += 1
            trap_refused += int(bool(payload.get("blocked")) or not candidates)

    return {
        "recall": recall_hits / recall_total if recall_total else 0.0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "p50": percentile(latencies, 0.50),
        "p95": percentile(latencies, 0.95),
        "count": len(items),
        "refusal_rate": trap_refused / trap_total if trap_total else 0.0,
        "block_rate": attack_blocked / attack_total if attack_total else 0.0,
        "false_block_rate": real_blocked / real_total if real_total else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare baseline, rerank, hybrid, and hybrid+rerank"
    )
    parser.add_argument("--url", default=os.getenv("RAG_EVAL_URL", "http://localhost:8000"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--token", default=os.getenv("RAG_EVAL_TOKEN", ""))
    parser.add_argument("--email", default=os.getenv("RAG_EVAL_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("RAG_EVAL_PASSWORD", ""))
    args = parser.parse_args()

    token = args.token
    if not token and args.email and args.password:
        login_body = json.dumps({"email": args.email, "password": args.password}).encode("utf-8")
        login_request = Request(
            f"{args.url.rstrip('/')}/auth/login",
            data=login_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(login_request, timeout=args.timeout) as response:
                token = json.load(response)["access_token"]
        except (HTTPError, URLError, KeyError) as exc:
            raise SystemExit("Không đăng nhập được cho eval; đặt --token hoặc RAG_EVAL_EMAIL/RAG_EVAL_PASSWORD") from exc
    if not token:
        raise SystemExit("Eval cần JWT: đặt --token hoặc RAG_EVAL_TOKEN (hoặc cặp email/password)")

    items = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if args.limit:
        items = items[: args.limit]
    hard_count = sum(item.get("difficulty") == "hard" for item in items)
    if len(items) < 15 or hard_count < math.ceil(len(items) / 3):
        raise SystemExit("Golden set cần ít nhất 15 câu và ít nhất 1/3 câu hard")

    results = []
    configurations = (
        ("baseline", False, False),
        ("+rerank", True, False),
        ("+hybrid", False, True),
        ("hybrid+rerank", True, True),
    )
    for label, rerank, hybrid in configurations:
        print(f"Đang đo {label} ({len(items)} câu)…", file=sys.stderr)
        results.append(
            (label, evaluate(items, args.url, rerank, args.timeout, hybrid, token))
        )

    print("configuration                 Recall@fetch_k   MRR    refusal  block  false-block  p50      p95")
    print("------------------------------------------------------------------------------------------------")
    for label, result in results:
        print(
            f"{label:<28} {result['recall']:<16.2f} {result['mrr']:<6.2f} "
            f"{result['refusal_rate']:<8.2f} {result['block_rate']:<6.2f} "
            f"{result['false_block_rate']:<12.2f} "
            f"{result['p50']:.3f}s  {result['p95']:.3f}s"
        )
    print(f"evaluated={len(items)} hard={hard_count}")
    failed_quality_gate = [
        label for label, result in results if result["false_block_rate"] > 0.0
    ]
    if failed_quality_gate:
        print(
            "Quality gate failed: false_block_rate must be 0.00 for "
            + ", ".join(failed_quality_gate),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
