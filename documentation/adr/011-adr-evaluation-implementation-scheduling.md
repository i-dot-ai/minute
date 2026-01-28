# ADR-XXXX: Initial Evaluation Implementation and Scheduling

## Status

Proposed

Date of decision: 2025-01-27

## Context and Problem Statement

When should evaluations run throughout the development and deployment lifecycle? We need to balance early detection of developer errors, prevention of production regressions, and monitoring for upstream provider changes. In this ADR we will focus on the initial implementation and scheduling of evaluations, rather than a final shape of the system.

## Considered Options

* Local checks with production models
* Local checks with local models
* Pre-PR checks
* Pre-deployment checks
* Scheduled production monitoring
* Combination of multiple stages [preferred]

## Decision Outcome

{Title of Option X}, because {summary justification / rationale}.

## Pros and Cons of the Options

### Local checks with production models

Run evaluations on the developer's local machine using the same models as production, requiring direct access to the AI infrastructure.

* Good, because it faciliates issues being spotted extremely early.
* Good, because results are directly comparable with production.
* Bad, because requires environment separation or dedicated service.
* Bad, because increases AI API costs.
* Bad, because it's harder to facilitate an enforcement mechanism.

### Local checks with local models

Run evaluations on the developer's local machine using locally-hosted models instead of production models.

* Good, because it faciliates issues being spotted extremely early.
* Good, because avoids additional AI API costs.
* Bad, because requires hardware capable of running AI models.
* Bad, because results not comparable with production, which hinders regression tracking.
* Bad, because it's harder to facilitate an enforcement mechanism.

### Commit checks

Run evaluations when a pull request is created or updated, before code is merged into the main branch.

* Good, because makes reverting easier than post-merge fixes.
* Good, because provides clear quality gate before integration.
* Good, because balances thoroughness with resource efficiency.
* Bad, because adds strain on CI/CD infrastructure.
* Bad, because may significantly slow down PR reviews.

### Pre-deployment checks

Run thorough evaluations before changes are deployed to production, after code has been merged.

* Good, because prevents regressions from reaching production.
* Good, because can run comprehensive evaluations without blocking development.
* Good, because catches issues specific to production-like environments.
* Bad, because issues require more effort to fix than earlier detection.
* Bad, because may delay deployments.

### Scheduled production monitoring

Run evaluations on a regular cadence (e.g., daily, weekly) against the production system without any code changes.

* Good, because detects regressions from upstream provider changes.
* Good, because establishes reference points for quality over time.
* Good, because identifies gradual degradation missed by deployment checks.
* Bad, because detects issues after they may have affected users.
* Bad, because incurs ongoing resource costs.

### Combination of multiple stages [preferred]

Implement evaluations at multiple stages with different levels of thoroughness: local checks for rapid iteration, pre-PR checks for quality gates, pre-deployment checks for final validation, and scheduled monitoring for production health. It's potentially beneficial to not use local-models in this options so that comparisons are more direct.

* Good, because balances early detection with comprehensive validation.
* Good, because addresses different failure modes across the lifecycle.
* Good, because enables different evaluation strategies per stage.
* Good, because enables rapid iteration while maintaining quality.
* Bad, because increases system complexity significantly.
* Bad, because it has by far the largest AI API cost.


### Alerting Mechanisms

Evaluations need to surface issues to the right people at the right time, this can be achieve through one of the following methods:

#### CI/CD Native Alerting [preferred]

Use the CI/CD platform's built-in notification system (e.g., GitHub Actions status checks, pipeline failure notifications).

* Good, because integrates seamlessly with existing workflows.
* Good, because requires no additional infrastructure.
* Bad, because insights only reach people with repository access.
* Bad, because scheduled evaluations may not reach the right people.

#### Dedicated Monitoring and Alerting Systems

Send evaluation results to dedicated monitoring platforms (e.g., CloudWatch, Datadog, PagerDuty) for alerting.

* Good, because aligns with production monitoring infrastructure.
* Good, because reaches people regardless of GitHub access.
* Bad, because requires additional infrastructure setup and access management.
* Bad, because it may require procuring additional subscriptions.

#### No Dedicated Alerting Infrastructure

Store evaluation results without implementing automated alerting, relying on manual review of stored results.

* Good, because fine-tuning thresholds is complex.
* Good, because avoids alert fatigue.
* Bad, because major issues may go unnoticed.

### Execution Infrastructure Options

Choice of infrastructure affects control, cost, and complexity. Since computational load is on external APIs, the execution environment mainly provides orchestration.

#### Standard CI/CD Runners [preferred]

Run evaluations on the CI/CD platform's default shared runners (e.g., GitHub Actions hosted runners).

* Good, because requires no additional infrastructure and management of resources.
* Bad, because limited control over environment and network access.
* Bad, because it may be more expensiver overall, especially for long executions. 

#### Dedicated CI/CD Runners

Deploy dedicated runners specifically for evaluation workloads (e.g. self-hosted GitHub Actions runners).

* Good, because provides control over environment and secrets.
* Good, because enables specific network contexts (e.g., VPC access).
* Bad, because requires infrastructure setup and maintenance.

### Storage Considerations

Results need storage for analysis, trend tracking, and debugging:

#### CI/CD Artifacts

Store evaluation results as build artifacts in the CI/CD system.

* Good, because integrates naturally with CI/CD workflows.
* Good, because provides easy access to results per build/PR.
* Bad, because it is not built for long-term persistence.
* Bad, because querying across artifacts is difficult.

#### S3 Bucket (or similar object storage) [preferred]

Store evaluation results as files in an S3 bucket or similar object storage.

* Good, because persistent and reliable.
* Good, because easy to set up and integrate.
* Good, because works well with custom dashboards.
* Bad, because not optimized for across-file querying of data.
* Bad, because requires a dashboard or jupyter notebook for most users.

#### Dedicated Database

Store evaluation results in a dedicated database (e.g., AuroraDB).

* Good, because enables powerful querying and analysis.
* Good, because supports technical users writing SQL queries.
* Good, because provides efficient time-series analysis.
* Good, because can serve dashboards or jupyter notebooks while supporting direct access.
* Bad, because requires infrastructure setup and maintenance.
* Bad, because non-technical users still need dashboard or jupyter notebook.

## Sign-off Required

### Local checks with production models

Enabling local evaluation checks with production models requires sign-off for:

* Increased API usage and direct access: Costs increase proportional to developers running evaluations locally.
* Environment separation or dedicated service: Requires environment separation or dedicated service for evaluation requests.

### Local checks with local models

Enabling local evaluation checks with local models requires sign-off for:

* Hardware requirements: All developers need capable hardware; may require upgrades.

### CI/CD evaluation stages (commit-level, pre-PR, pre-deployment)

Finer-grained evaluation stages incur higher costs and require sign-off for:

* Budget allocation: Frequent evaluation runs significantly increase inference costs.
* Infrastructure resources: CI/CD capacity may need expansion.
