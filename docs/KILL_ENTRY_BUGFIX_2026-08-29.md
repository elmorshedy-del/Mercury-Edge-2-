# Kill-entry placement bug — 2026-08-29

## Original strategy placement bug

Mercury Edge 2 correctly detected factual dead-bucket conditions, but could still produce zero paper trades.

The original `KillEngine.on_proof()` had two terminal pre-entry filters:

1. If the dead bucket's YES bid was missing or below `min_bid_cents` (15c), the engine immediately added `(ticker, kill_level)` to `CityState.fired`.
2. If the YES bid/ask spread exceeded `max_spread_cents` (5c), the engine also immediately added the bucket to `fired` and skipped it.

That behavior was incompatible with the strategy's actual edge. Immediately after a definitive temperature proof, the ask can move first while a stale resting YES bid remains. A wide spread is therefore not evidence against the trade; it can be the exact stale-liquidity state the kill strategy is designed to capture.

There was a second compounding bug: once `proven_max` advanced, equal or lower follow-up proof events returned before re-evaluating the already-dead bucket. Therefore a transient thin/empty quote at the first proof snapshot permanently suppressed that kill opportunity.

Observed production symptom: city states accumulated many `fired` buckets while `paper_ledger.jsonl` remained empty.

## Fix

`engine/strategy.py` now follows these rules:

- A factual kill is evaluated against the resting YES bid; the ask/spread is not an entry gate.
- A missing or sub-15c bid is **retryable** and does not mark the bucket fired.
- Equal/lower follow-up proof traffic re-checks all buckets already dead under the monotone `proven_max`.
- A bucket is marked fired only when the strategy actually emits an intent.
- Top-tail exclusion and the DSM/OMO physical-plausibility guard are unchanged.

## Regression coverage

`research/replay_test.py` now includes the original failure pattern:

1. Proof kills the 81–82 bucket at 83F.
2. First quote is 10/64: no intent, but the bucket must remain retryable.
3. Same-level proof is seen again with 34/64: despite the 30c spread, the engine must emit the kill intent.
4. Subsequent proofs must dedupe after the intent fires.

This preserves the original strategy premise: **trade only mathematically dead buckets, but do not let transient market microstructure suppress a valid stale-bid execution.**
