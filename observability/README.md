# Observability — token & cost telemetry

A local-first stack that turns Claude Code's built-in OpenTelemetry into dashboards:

```
Claude Code  --OTLP-->  OTel Collector  --scrape-->  Prometheus  -->  Grafana
```

It complements `hooks/cache-meter.sh`: the hook prints an inline per-turn cache
read-rate (the nudge); this stack is the durable, queryable layer — cost and tokens
by model, the cache split, trends, and per-issue spend.

## 1. Bring up the stack

```
docker compose -f observability/docker-compose.yml up -d
```

- Grafana → http://localhost:3000 (anonymous admin; Prometheus datasource pre-provisioned)
- Prometheus → http://localhost:9090 (check `/targets` to see the collector is up)
- Collector intake → `localhost:4317` (OTLP gRPC), `:4318` (HTTP); scrape endpoint `:8889`

## 2. Enable telemetry in Claude Code

It's wired in `../settings.json` (the `env` block) but defaulted **off**. Flip it:

```jsonc
"CLAUDE_CODE_ENABLE_TELEMETRY": "1"
```

…or export for a one-off session instead:

```
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Metrics export every ~60s, logs every ~5s by default — run a few turns before
expecting data.

## 3. What you get

- **Metrics** — token usage by model with the **cache-read vs cache-creation**
  split, plus cost; session-scoped (`session.id`).
- **Events (logs)** — `user_prompt`, `api_request`, `tool_result`, assistant
  responses, tied to a `prompt.id`.
- **Traces** (optional beta) — a span per model request / tool execution: set
  `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` and `OTEL_TRACES_EXPORTER=otlp`.

> The exact metric/event **names** aren't fully enumerated in the public docs.
> Confirm them against the Claude Code monitoring reference
> (https://code.claude.com/docs/en/monitoring-usage) and Prometheus' metric browser
> before pinning PromQL — the panel list below uses indicative names.

## 4. Attribution for the issue-loop

Native metrics are session-scoped, so to get **cost per issue** run each issue's
worker as its own session/agent (the loop already isolates work per issue) — a
session then maps to one issue. Tag a whole run with resource attributes:

```
export OTEL_RESOURCE_ATTRIBUTES="loop.run=$(date +%s),service.name=agentic-eng"
```

Panels worth building (names indicative — verify first):

- **Cost / tokens by `model`** → makes the Sonnet-vs-Opus tiering call from
  `CONTEXT-ENGINEERING-REVIEW.md` evidence-based.
- **Cache read-rate trend** → confirms caching is working (cross-check `cache-meter`).
- **Cost per session (≈ per issue)** → surfaces the expensive issues and gates.
- **Throughput vs concurrent spend** → with parallel mode on, is `N > 1` paying off?

## 5. Tear down

```
docker compose -f observability/docker-compose.yml down
```

The hook's `.cache-metrics.log` stays local and gitignored; this stack writes only
to container volumes. Add `observability/` build artifacts to `.gitignore` if you
later add exported dashboards or volumes.
