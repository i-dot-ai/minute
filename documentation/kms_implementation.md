***

# AWS KMS Implementation
This documents the current state of encryption for the `i-ai-minute` architecture. The audit was conducted to verify compliance with **UK Government NCSC Cloud Security Principle 2 (Asset Protection) **UK Government NCSC Cloud Security Principle 2 (Asset Protection)**  
<https://www.ncsc.gov.uk/collection/cloud/the-cloud-security-principles/principle-2-asset-protection-and-resilience>
 and departmental governance standards for "Official-Sensitive" data, specifically regarding the use of Customer Managed Keys (CMKs) versus default AWS encryption (SSE-S3).

## 1. Summary

The `i-ai-minute` infrastructure **is currently using Customer Managed Keys (CMKs)** via AWS KMS for data at rest across S3, RDS, and SSM Parameter Store. The application does not rely on default AWS managed encryption. Permissions are properly scoped to specific ECS Task Roles. This configuration successfully enables **Cryptographic Erasure** (the ability to instantly revoke access to all data by disabling the key) and ensures granular auditing via AWS CloudTrail.

---

## 2. Methodology

The audit involved a thorough review of the Terraform Infrastructure as Code (IaC) repository for the `i-ai-minute` project. The following components were specifically targeted:
- AWS S3 bucket definitions (`terraform/s3.tf`)
- AWS RDS Aurora cluster definitions (`terraform/rds.tf`)
- IAM policies and ECS Task Execution Roles (`terraform/iam.tf`, `terraform/ecs.tf`)
- SSM Parameter Store secrets definitions (`terraform/secrets.tf`)

---

## 3. Current State: Encryption by Component

We have confirmed that CMKs are implemented for primary data storage and secret management components:

| Component | Encryption Strategy | Resource / Logic |
| :--- | :--- | :--- |
| **S3 Buckets** | CMK (SSE-KMS) | `terraform/s3.tf` passes `kms_key_arn` to the `app_bucket` module to encrypt the data bucket. |
| **RDS (Aurora)** | CMK (Storage Encrypted) | `terraform/rds.tf` passes the `kms_key_arn` to the `rds` module to encrypt the database cluster. |
| **SSM Parameters** | `SecureString` with CMK | `terraform/secrets.tf` explicitly uses the platform KMS key for all `SecureString` parameter definitions. |

**Assessment:** The "Default Encryption" risk has been successfully mitigated. We are using CMKs for all critical storage and configuration.

---

## 4. Key ARN Identification and Administration

The KMS Key ARNs are not managed within the local `i-ai-minute` Terraform code. They are centralized and managed as part of the shared, upstream **platform infrastructure**.

- **Key Reference:** `data.terraform_remote_state.platform.outputs.kms_key_arn`
- **Source:** The exact ARN is defined and outputted by the `platform` workspace in the central Terraform S3 state bucket.

This centralized approach ensures consistency but means any administrative actions on the key itself (such as rotation or deletion) must be orchestrated through the platform repository.

---

## 5. Key Policy and Permissions Review

Granular auditing and strict access control are core requirements for Official-Sensitive workloads. 

- **Policy Definition:** The `ecs_exec_custom_policy` explicitly grants the necessary KMS permissions: `kms:Decrypt`, `kms:Encrypt`, `kms:GenerateDataKey`, and `kms:DescribeKey`.
- **Scope Restriction:** Crucially, these permissions are **not wildcarded** (`*`). They are restricted strictly to the specific `kms_key_arn` retrieved from the platform state.
- **Role Assignment:** This policy is attached only to the **ECS Task Roles** for the specific services that require it: `backend`, `frontend`, and `worker`.
- **Auditing:** Any decryption or encryption action performed by these specific roles using the CMK will log detailed, identifiable events in AWS CloudTrail.

---

## 6. Key Rotation Status

Key rotation configuration was investigated within the repository:

- **Finding:** No `enable_key_rotation` attribute or equivalent configuration was found in the local `.tf` files.
- **Rationale:** Because the KMS key is defined and managed in the upstream `platform` infrastructure, the rotation setting must be configured and verified within that specific repository.

---

## 7. Potential Improvements

The Terraform codebase confirms the implementation of CMKs, meeting the objective of avoiding default S3/RDS encryption and satisfying NCSC principles for asset protection.

### Recommendations for Follow-up

1. **Verify Platform Key Settings:** Confirm that `enable_key_rotation = true` is set in the `platform` repository for the key referenced by `kms_key_arn` to ensure compliance with key lifecycle policies.
2. **Review Platform Key Policy:** Verify the JSON Key Policy (resource policy) in the `platform` repository to ensure no overly permissive wildcards are used in the key's own policy document.
3. **Live Environment Spot-Check:** While the code reflects CMK usage, a manual spot-check in the AWS Console for the production data bucket (e.g., `i-dot-ai-prod-minute-data`) is recommended to provide secondary validation that the live environment exactly mirrors the Terraform configuration.

***
