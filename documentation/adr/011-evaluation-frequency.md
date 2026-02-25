# ADR-011: Evaluation Frequency

## Status

Proposed

Date of decision: 2025-01-27

## Context and Problem Statement

When should evaluations run throughout the development and deployment lifecycle? We need to balance early detection of developer errors, prevention of production regressions, and monitoring for upstream provider changes.

## Considered Options

* Commit checks
* Pre-deployment checks
* Scheduled live regression monitoring
* Scheduled alternate provider comparison monitoring

## Decision Outcome

We will implement scheduled live regression monitoring and pre deployment checks. Scope may expand or costs reduce via a pre deployment flag, depending on evaluation running costs. Alternative provider monitoring is not a current priority and will be considered later, subject to cost. Commit checks will be added only if costs are low and lack of granularity impacts delivery speed.

## Pros and Cons of the Options

### Commit checks

Run evaluations when a pull request is created or updated, before code is merged into the main branch.

* Good, because makes reverting easier than post-merge fixes.
* Good, because provides clear quality gate before integration.
* Bad, because adds significant strain on CI/CD infrastructure.
* Bad, because may significantly slow down PR reviews.
* Bad, because increases API costs for every PR iteration.
* Bad, because creates friction in development workflow.

### Pre-deployment checks

Run thorough evaluations before changes are deployed to production, after code has been merged. Can be made optional if costs are substantial, with strategic decisions on whether specific deployments affect AI-related code that would warrant evaluation.

* Good, because prevents regressions from reaching production.
* Good, because can run comprehensive evaluations without blocking development.
* Good, because catches issues specific to production-like environments.
* Good, because can be selectively applied based on code changes.
* Bad, because issues require more effort to fix than earlier detection.
* Bad, because may delay deployments.
* Bad, because determining when to run requires judgment about AI code impact.

### Scheduled live regression monitoring

Run evaluations on a regular cadence (e.g., daily, weekly) against the live system without any code changes.

* Good, because detects regressions from upstream provider changes.
* Good, because establishes reference points for quality over time.
* Good, because identifies gradual degradation missed by deployment checks.
* Bad, because detects issues after they may have affected users.
* Bad, because incurs ongoing resource costs.

### Scheduled alternate provider comparison monitoring

Run evaluations at a less frequent cadence (e.g., monthly, quarterly) comparing current provider against alternative providers to assess whether model choices remain competitive.

* Good, because prevents falling behind with outdated models.
* Good, because informs strategic decisions about provider selection.
* Good, because lower cadence reduces costs compared to frequent monitoring.
* Bad, because incurs additional API costs across multiple providers.
* Bad, because determining best providers to compare against is challenging.
* Bad, because cost and data governance may make comprehensive provider coverage infeasible.

## Appendix

### Ad-hoc local checks with production models

While not a frequency-based consideration, developers should be able to run ad-hoc local evaluations using production models to verify changes before deployment, particularly when working on AI-related system components.

* Good, because enables developers to validate changes early.
* Good, because results are directly comparable with production.
* Bad, because requires environment separation or dedicated service.
* Bad, because increases AI API costs based on usage.
