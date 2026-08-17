# Infrastructure Decisions

This file records infrastructure choices that have already been evaluated and should not be reopened from scratch during routine development.

A decision marked **Active** remains the default until one of its explicit reopen conditions is met or new measurements materially invalidate the assumptions behind it.

## Serverless GPU platform decision

**Status:** Active for the current Surya/serverless OCR benchmark.

**Target platform and region:** AWS Israel (Tel Aviv), `il-central-1`.

### Decision

Use AWS `il-central-1` as the preferred target for the serverless GPU OCR benchmark.

Google Cloud `me-west1` with an NVIDIA T4 was evaluated and rejected as the preferred target for the intended Surya workload because the T4's 16 GB VRAM and available performance margin are too tight for the target server-side OCR path.

The preferred AWS GPU class is G5 / NVIDIA A10G 24 GB, subject to actual `il-central-1` availability, account quota, and benchmark cost.

This is a benchmark/platform decision, not a permanent vendor lock-in. The purpose is to stop repeatedly reopening an already evaluated Google-vs-AWS branch without new evidence.

### Reopen Google only if

- a larger economical GPU becomes available for the required workload in Google Cloud `me-west1`;
- measured Surya resource usage shows that a T4 is comfortably sufficient with acceptable latency and safety margin;
- AWS `il-central-1` becomes unavailable for the required GPU class or quota cannot reasonably be obtained;
- AWS becomes materially more expensive for the measured production workload.

### Development rule

Until one of the reopen conditions is met, infrastructure work should proceed from the assumption:

```text
Serverless GPU OCR benchmark target = AWS il-central-1.
Preferred GPU class = G5 / NVIDIA A10G 24 GB, subject to availability/quota.
Google T4 is not the default candidate.
```

Do not spend development cycles re-comparing Google T4 and AWS from zero unless new measurements or provider availability satisfy a reopen condition.
