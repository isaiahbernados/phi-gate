# Initial validation — 2026-10-06

- 27 deterministic tests passed on Python 3.12.13: native decision contract,
  hosted response contracts, precedence, input bounds, strict booleans, malformed
  responses, refusal/truncation, timeout, redirects, and PHI-safe error handling.
- Package built and installed in isolated Python 3.13.7 environment; console
  entrypoint checked separately.
- Packaged skill passed Codex skill-creator's `quick_validate.py`.
- Live local Ollama 0.35.0, `tev1:4b` (installed model ID `cef45ef93cf6`),
  threshold `0.5`: **24/24 synthetic cases matched**, zero provider errors,
  zero false negatives, zero false positives. Median subprocess-plus-inference
  time **204 ms**, warm model on this machine.

Reproduce live check with `python3 scripts/evaluate.py --model tev1:4b`.
Case set: `tests/synthetic.json`. No real patient data used. One small English
smoke set cannot establish production PHI accuracy, calibration, or adversarial
robustness. Hosted Jev/OpenAI adapters tested against local contract fixtures;
no hosted credentials or live hosted calls used.
