# phi-gate

One input, one model request, one boolean for potential PHI. Pipe arbitrary logs,
API responses, or agent-observed text into a configurable decision model.
No runtime dependencies; Python 3.11+.

```sh
phi-gate --file log.txt
# true
curl --fail --silent --show-error https://example.invalid/api | phi-gate
```

The pipeline is illustrative. In real integrations, verify upstream fetch
succeeded before classifying its body; a successful classifier does not validate
an upstream command's status.

## Install

```sh
gh repo clone isaiahbernados/phi-gate && cd phi-gate
uv tool install .
```

Without uv: `python3 -m venv .venv`, then `.venv/bin/pip install .` and
`.venv/bin/phi-gate`. Direct zero-install usage: `python3 phi_gate.py`.

## Local System One model (default)

Install [Ollama 0.35+](https://ollama.com/download), start its server (`ollama serve`
if the desktop app is not running), then:

```sh
ollama pull tev1:4b
printf '%s' 'GET /health returned 200' | phi-gate
```

Uses native [`POST /v1/systemone`](https://ollama.com/library/tev1), asking one
Noul question and comparing `answers.phi.noul >= threshold` (default `0.5`).
This is decision scoring, not a chat prompt forced into JSON.
For alternatives: `ollama pull nimble` and `phi-gate --model nimble`, or
`ollama pull tev1:0.8b` and `phi-gate --model tev1:0.8b`.
Loopback requests bypass ambient HTTP proxies.

## Hosted models

Native [TypeSafe Jev](https://docs.typesafe.ai/api), keys from
[TypeSafe console](https://console.typesafe.ai/keys):

```sh
export TYPESAFE_API_KEY='your-key'
phi-gate --provider jev --file log.txt
```

Another Jev-compatible server:

```sh
export PHI_GATE_API_KEY='your-key'
phi-gate --provider systemone --base-url https://your-server.example --model your-model --file log.txt
```

OpenAI uses the documented [Responses API with strict structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses),
default [`gpt-4.1-nano`](https://developers.openai.com/api/docs/models/gpt-4.1-nano):

```sh
export OPENAI_API_KEY='your-key'
phi-gate --provider openai --file log.txt
```

This adapter is a small-model classification fallback, not native System One
inference. It requests `store=false`. No separate OpenAI “Decisions API” contract
was established from official docs during implementation; no guessed endpoint
is used.

OpenAI-compatible chat servers must support strict JSON-schema responses:

```sh
export PHI_GATE_API_KEY='your-key'
phi-gate --provider chat --base-url https://your-server.example/v1 --model your-model --file log.txt
```

Bases for `ollama`, `jev`, and `systemone` exclude `/v1`; CLI appends
`/v1/systemone`. Bases for `openai` and `chat` include API prefix, usually `/v1`;
CLI appends `/responses` or `/chat/completions`. Remote endpoints require HTTPS;
redirects are rejected. Full text goes to the configured provider. Hosted data
handling and contractual suitability depend on that provider and account.

## Configure

Optional flat TOML config: `--config PATH`, `PHI_GATE_CONFIG`, or
`$XDG_CONFIG_HOME/phi-gate/config.toml` (default `~/.config/phi-gate/config.toml`).
Start from [config.example.toml](config.example.toml). Explicit missing/malformed
config fails; missing default config uses defaults.

Priority: **flags > environment > TOML > defaults**.

| Flag | Environment | Default |
| --- | --- | --- |
| `--provider` | `PHI_GATE_PROVIDER` | `ollama` |
| `--model` | `PHI_GATE_MODEL` | Provider default; required for `chat`/`systemone` |
| `--base-url` | `PHI_GATE_BASE_URL` | Provider default; required for `chat`/`systemone` |
| `--api-key-env` | `PHI_GATE_API_KEY_ENV` | `TYPESAFE_API_KEY`, `OPENAI_API_KEY`, or `PHI_GATE_API_KEY` |
| `--threshold` | `PHI_GATE_THRESHOLD` | `0.5`; native System One only |
| `--timeout` | `PHI_GATE_TIMEOUT` | `30` seconds |
| `--max-input-bytes` | `PHI_GATE_MAX_INPUT_BYTES` | `1024` UTF-8 bytes |

`PHI_GATE_API_KEY` overrides the selected key environment variable. Keys stay in
environment, never TOML or flags. HTTP/auth failures are explicit errors; no
automatic retries or provider fallback. Lower native thresholds flag more inputs;
select a threshold using evaluations of your workload, not synthetic examples alone.

Input limit deliberately stays small for experimental decision models. Oversized
input fails without truncation; CLI never silently skips text. Raise the byte limit
only after checking the selected model's actual usable context budget, including
the policy/question. Byte limits are not tokenizer-aware. Classify complete
records: separately checking fragments can miss an identifier linked to health
information across their boundary.

## Client contract

Read stdin by default, or `--file PATH` (`--file -` means stdin). Input must be
nonempty UTF-8. No sensitive text in command arguments needed.

| Exit | Stdout | Meaning |
| --- | --- | --- |
| `0` | `true` + newline | Potential PHI detected |
| `0` | `false` + newline | Model did not flag PHI |
| `2` | Empty | Unknown/error; fixed diagnostic on stderr |
| `130` | Empty | Interrupted |

Both decisions exit 0. Do not use shell success as the PHI verdict. Never convert
an error, refusal, invalid JSON, incomplete output, or timeout into `false`.
Tool prints neither submitted text nor provider error bodies. It does not write
input to files, although the caller and provider control their own logging.

Python API:

```python
from phi_gate import Config, classify
phi: bool = classify(api_response_text, Config(model="tev1:4b"))
```

Subprocess clients and agents:

```python
import json, subprocess
r = subprocess.run(["phi-gate"], input=text, text=True, capture_output=True)
r.check_returncode()
phi = json.loads(r.stdout)
assert type(phi) is bool
```

## Agent skill

Packaged under [skills/phi-gate/SKILL.md](skills/phi-gate/SKILL.md). From repository
root, install project-locally for Codex:

```sh
mkdir -p .agents/skills && cp -R skills/phi-gate .agents/skills/
```

For Claude Code, use `.claude/skills/` instead. For global Codex discovery, copy
to `${CODEX_HOME:-$HOME/.codex}/skills/`. Copying into an existing skill directory
should follow your normal update process. Skill installation is separate from CLI
installation; CLI must remain on the agent's PATH.

## Scope and validation

Policy screens potentially identifiable health, care, and healthcare payment
information; patient-linked IDs count conservatively. Unrelated personal data
and general medical knowledge do not automatically count. Based on
[HHS PHI guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html).
Actual legal PHI status also depends on holder and context unavailable in arbitrary
text. A `false` result is a screening judgment, not proof of de-identification or
authorization to disclose. Prompt injection instructions are treated as data;
model resistance is not guaranteed.

Run deterministic contract/error tests:

```sh
python3 -m unittest discover -s tests -v
```

Run live evaluation on 24 synthetic English records (never real patient data):

```sh
python3 scripts/evaluate.py --model tev1:4b --output eval.json
```

Other CLI flags pass through. Evaluation reports false negatives, false positives,
errors, case IDs, and end-to-end latency; it never reports source text. Exit 0 means
all synthetic labels matched, 1 means mismatches, 2 means provider failures.
These smoke cases do not establish production accuracy or probability calibration.
Hosted adapters have deterministic contract tests; live tests require your keys.
