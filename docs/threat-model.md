# AcademiaHub — Threat Model

> **Version:** 1.0 · **Date:** 30 Sep 2026 · **Status:** Draft (to be reviewed before Phase 1 ships)

---

## 1. Assets to Protect

| Asset | Sensitivity | Notes |
|---|---|---|
| User credentials (passwords, MFA secrets) | Critical | Argon2id hashed; MFA secrets field-encrypted |
| Personal data (name, email, institution) | High | DPDP Act 2023 + GDPR obligations |
| Paid content (topics, files behind paywall) | High | Revenue-impacting if leaked |
| Uploaded files and downloads | High | Signed URLs only; private S3 bucket |
| Student progress and quiz data | Medium | Privacy-sensitive |
| Audit log | High | Must be append-only; tampering hides attacker actions |
| Infrastructure secrets (DB creds, AWS keys) | Critical | Never in source; GitHub Actions Secrets only |

---

## 2. Threat Actors

| Actor | Motivation | Capability |
|---|---|---|
| Unauthenticated scrapers | Harvest free content, email lists | Low–Medium |
| Malicious students | Bypass paywall, exfiltrate files | Low–Medium |
| Malicious code submitters | Sandbox escape, DoS via runaway code | Medium |
| Compromised editor account | Publish harmful content | Medium |
| External attacker | Data breach, ransomware | High |
| Insider threat (staff) | Data export, privilege abuse | Medium |

---

## 3. Attack Vectors & Mitigations

| Vector | Risk | Mitigation |
|---|---|---|
| Credential stuffing / brute force | Account takeover | Rate limiting, lockout, MFA for staff |
| SQL injection | Data breach | Parameterised queries (ORM only); no raw SQL |
| XSS via content blocks | Session hijack, data exfiltration | Markdown sanitised on output; strict CSP |
| CSRF | State-changing requests from malicious sites | Django CSRF middleware; SameSite cookies |
| Insecure direct object reference (IDOR) | Access other users' data or files | Server-side permission check on every request |
| Exposed download URLs | File sharing without auth | Signed S3 URLs expiring in 60 s; never public |
| Code sandbox escape | RCE on host | Containers with gVisor/Firecracker (Phase 5); no network; CPU/memory caps |
| Dependency vulnerabilities | Supply-chain compromise | `pip-audit` + `npm audit` in CI; Dependabot PRs |
| Secret leakage in logs | Credential exposure | Structured logging; secrets never logged |
| Insecure file upload | Malware delivery, path traversal | Virus scan before publish; randomised S3 keys |
| Mass data export | Privacy breach | Per-user daily download quota; admin export requires MFA + audit log |

---

## 4. Trust Boundaries

```
Internet → CloudFront/WAF → Load Balancer → ECS (API / Web)
                                              │
                                             RDS (private subnet, no internet)
                                             ElastiCache (private subnet)
                                             S3 (private bucket, VPC endpoint)
                                              │
                                         Code Runner (isolated runner_net, no egress)
```

- All internal service-to-service communication stays within the VPC.
- The code runner has **no** access to the database, Redis, or the internet.
- S3 bucket has **no** public access policy; files are served only via signed URLs.

---

## 5. Open Items (resolve before Phase 1 ships)

- [ ] Confirm legal review of DPDP Act 2023 obligations with a lawyer
- [ ] Define data retention periods for each table
- [ ] Choose a WAF ruleset (AWS Managed Rules baseline at minimum)
- [ ] Decide on a vulnerability disclosure / bug-bounty policy
- [ ] Document incident response runbook (`docs/runbooks/incident-response.md`)
