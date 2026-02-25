# ADR-014: Evaluation Runners

## Status

Proposed

Date of decision: 2025-01-27

## Context and Problem Statement

Choice of execution infrastructure affects control, cost, and complexity. Since computational load is on external APIs, the execution environment mainly provides orchestration. Modern CI/CD platforms provide robust security features including secrets management, audit logging, and access controls. We need to determine where evaluation workloads should run.

## Considered Options

* Standard CI/CD Runners
* Dedicated CI/CD Runners

## Decision Outcome

Standard CI/CD Runners, because they provide robust security features comparable to dedicated infrastructure while avoiding infrastructure management overhead and costs.

## Pros and Cons of the Options

### Standard CI/CD Runners

Run evaluations on the CI/CD platform's default shared runners (e.g., GitHub Actions hosted runners).

* Good, because requires no additional infrastructure and management of resources.
* Good, because logs integrate naturally with CI/CD workflows.
* Good, because modern CI/CD platforms provide robust security features including secrets management, audit logging, and access controls.
* Good, because widely trusted and used across the industry with strong security track records.
* Bad, because limited control over environment and network access compared to dedicated infrastructure.

### Dedicated CI/CD Runners

Deploy dedicated runners specifically for evaluation workloads (e.g. self-hosted GitHub Actions runners).

* Good, because provides isolation with stricter access controls and audit logging.
* Good, because ensures sensitive data never touches shared infrastructure.
* Good, because provides control over secrets management and network policies.
* Bad, because requires infrastructure setup and maintenance.
* Bad, because adds complexity for orchestration and CI/CD integration.
* Bad, because requires sign-off for infrastructure costs (compute resources for self-hosted runners).
* Bad, because requires sign-off for maintenance overhead (managing runner infrastructure, updates, and security).
* Bad, because may require sign-off for network configuration (VPC setup and access controls if required).
* Bad, because certain stages can trigger running code by a member of the public.

