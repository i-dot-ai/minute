# ADR-012: Evaluation Storage

## Status

Proposed

Date of decision: 2025-01-27

## Context and Problem Statement

Evaluation systems require storage for both inputs (test cases, prompts, configurations) and outputs (results, metrics, scores). These have fundamentally different characteristics:

Inputs are infrequently written (only when tests are added or modified), could contain sensitive data (real transcripts, confidential content), and require stricter access control. They need version control for reproducibility and code review for changes.

Outputs are frequently written (every evaluation run), contain primarily metrics and scores, and need to be queryable for trend analysis and debugging. They require efficient storage and retrieval for dashboards and analysis tools.

We need to determine optimal storage strategies that address these distinct requirements, with particular emphasis on protecting sensitive input data.

## Considered Options

### Input Storage Options
* Git repository (version controlled test cases)
* S3 Bucket (versioned test datasets)
* Dedicated test case database

### Output Storage Options
* CI/CD Artifacts
* S3 Bucket (or similar object storage)
* Dedicated Database

## Decision Outcome

Inputs: S3 Bucket (versioned test datasets), because it handles large files efficiently, supports fine-grained access control for sensitive data, provides encryption and audit logging, and enables versioning to track dataset evolution.

Outputs: S3 Bucket (or similar object storage), because it provides persistent and reliable storage, is easy to set up and integrate, and works well with custom dashboards or jupyter notebooks for analysis.

## Pros and Cons of the Options

### Input Storage Options

#### Git repository (version controlled test cases)

Store evaluation test cases, prompts, and configurations in the git repository alongside code.

* Good, because no additional infrastructure required.
* Good, because it is easy to configure and use.
* Bad, because not suitable for large binary test files (e.g., audio samples).
* Bad, because it is completely unsuitable for sensitive data.

#### S3 Bucket (versioned test datasets)

Store evaluation inputs as versioned files in S3 bucket with lifecycle policies.

* Good, because handles large files efficiently and stores binary test data.
* Good, because supports fine-grained IAM policies and encryption for sensitive data.
* Good, because CloudTrail provides audit logs for access.
* Good, because versioning tracks dataset evolution.
* Good, because it is well suited for storing sensitive data, if configured correctly. 
* Bad, because it requires additional setup and access management.

#### Dedicated test case database

Store test cases and configurations in a dedicated database with versioning.

* Good, because enables querying and filtering test cases.
* Good, because can implement row-level security for sensitive test cases.
* Good, because it is well suited for storing sensitive data, if configured correctly. 
* Bad, because requires infrastructure setup and maintenance.
* Bad, because it requires additional access management.

### Output Storage Options

#### CI/CD Artifacts

Store evaluation results as build artifacts in the CI/CD system.

* Good, because integrates naturally with CI/CD workflows.
* Good, because provides easy access to results per build/PR.
* Bad, because it is not built for long-term persistence.
* Bad, because querying across artifacts is difficult.

#### S3 Bucket (or similar object storage)

Store evaluation results as files in an S3 bucket or similar object storage.

* Good, because persistent and reliable.
* Good, because easy to set up and integrate.
* Good, because works well with custom dashboards.
* Good, because enables versioning and lifecycle policies for cost management.
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

## Storage Content Requirements

### Input Storage Should Include
* Test prompts and cases
* Model configurations and parameters
* Dataset versions and references
* Expected outputs or ground truth
* Test case metadata (tags, categories, difficulty)

### Output Storage Should Include
* Evaluation metrics and scores
* Pass/fail status
* Timestamps and execution metadata
* Model versions and configurations used
* Reference to input version used
* Individual test case results
