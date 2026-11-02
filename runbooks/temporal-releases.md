# Release the application and Temporal separately

```console
make release env=dev                  # frontend, backend and application worker
make release-temporal-server env=dev  # build and release only the Temporal server
```

Application releases use `terraform/`; server releases use `terraform-temporal/`, with separate state. The server image is built only during a server release. Both commands release the current **committed** revision, not uncommitted files. Terraform 1.7 or newer is required.

Search attributes are managed manually through the Temporal CLI, not by releases. [Register and verify them](temporal.md#rollout-and-limits) in each namespace before deploying application code that writes them.

Application releases check `UserId`, `TranscriptionId`, `MinuteId` and `MinuteVersionId` are all **Keyword** before applying the application Terraform root. The check runs as the deployed one-off Temporal admin task, inside the VPC. It does not change attributes or deploy Temporal. A missing/wrong-type attribute, unreachable server or failed check stops the release; task diagnostics are printed from CloudWatch when permitted. The deployment role needs `logs:GetLogEvents` in addition to the existing task permissions. You can run it independently with `make check_temporal_search_attributes env=dev`.

Release the updated Temporal server/admin image before the first app release using this check. An older admin image without `check-search-attributes` fails closed. The namespace task still does not create search attributes: registration remains manual.

## What a server release does

Every explicit server release builds separate server and admin images at the version in `temporal/version.env`. Both are pushed to the existing `minute-temporal` ECR repository: `<commit-sha>` for the server and `<commit-sha>-admin` for admin tools. The release then:

1. Provisions the database and one-off admin task definition without updating the running server.
2. Runs the admin task to initialise empty databases or apply missing schema migrations to both databases. An up-to-date schema is a no-op; any failure stops the release before server rollout.
3. Deploys the server and waits for ECS readiness.
4. Runs a namespace task, creating `default` only if it is absent. Failure marks the release unsuccessful.

There is no continuously running admin service. Server restarts do not run migrations. The server uses `temporal_runtime`, a non-owner database user; only the schema task receives master credentials. The release's targeted Terraform apply is restricted to admin-task provisioning; the subsequent apply covers the whole server stack.

No additional ECR repository is needed. The build role needs push permission on `minute-temporal`. The deployment role/permissions boundary must permit the admin task's IAM role, `ecs:RunTask`, task inspection and `iam:PassRole`. Task logs are in `/ecs/i-dot-ai-<env>-minute-temporal-admin`. Environment tags are separate too: `dev`/`preprod`/`prod` for the server and `dev-admin`/`preprod-admin`/`prod-admin` for admin tools.

For local development, Compose runs the same schema and namespace steps as one-off services. Start through `make run` so both images receive `temporal/version.env`.

## First release of the split configuration to dev

Dev is disposable, so recreate Temporal rather than transfer its state. **This deletes dev's Temporal database and workflow history, not the application's database.** Do not run another release during cleanup, and do not submit recordings until the new server is healthy.

### 1. Commit and push the new configuration

Include the new `terraform-temporal/` directory, application outputs, release changes and tests, and the deletion of `terraform/temporal.tf`. Wait for the application image builds and checks to pass.

### 2. Provision application infrastructure and let Terraform clean up

```console
make tf_apply env=dev IMAGE_TAG=<committed-SHA-with-built-application-images>
```

This is an explicit, reviewed bootstrap Terraform apply, not a normal app release: it provisions the application networking outputs required by Temporal before the server exists. It can start application containers, but do not submit jobs until Temporal and its attributes are ready. On this first apply, Terraform deletes the old Temporal resources because they are no longer in the application configuration. The application database stays in the application configuration and is not removed. Normal `make release` is blocked at this point by the new preflight.

If cleanup fails, or the old Temporal resources were previously forgotten from application state, stop and investigate before creating same-named replacements. Transcription will be unavailable until the server is created.

### 3. Release the standalone Temporal server

```console
make release-temporal-server env=dev
```

Wait for **release-infrastructure** to finish successfully. Confirm the Temporal ECS service is healthy, then [register the four Keyword attributes](temporal.md#rollout-and-limits). Run `make release env=dev`; its preflight must pass before the normal application rollout. Once the application worker is running, test an upload. If state access is denied, the deployment role needs access to the new `minute-temporal/terraform.tfstate` key under the dev workspace prefix.

## Subsequent releases

Release application changes with `make release env=dev`; Temporal stays running. Release changes to the server image/configuration with `make release-temporal-server env=dev`; application containers stay unchanged. Check Temporal's upstream upgrade requirements before changing its version.

For a fresh preprod or production environment, provision the initial application infrastructure with a reviewed bootstrap Terraform apply, release `temporal-server`, register the four ID attributes, then release `app`. Normal app releases deliberately do not bypass the preflight for a fresh environment. For production, server/app releases use **release-infrastructure** manually on `main`. No state migration is needed for either environment.

## Before production and version upgrades

Rehearse in preprod with existing workflows: release, restart the server, and confirm the data survives. Production server releases require checking **server_upgrade_reviewed** in the manual workflow. Review Temporal's supported version sequence and schema compatibility before ticking it; this acknowledgement is not an automatic compatibility check.

Aurora has deletion protection outside dev and 35-day automated backups. Before an upgrade, verify backups and recovery access, and take a manual snapshot when required by the upgrade plan. Restore to a separate cluster from a known-good snapshot or point-in-time, confirm its workflow data, and switch endpoints only after verification. Do not delete the original cluster until recovery is validated. The shared RDS module skips final snapshots on deletion, so deletion protection is not a substitute for backups.

Schema migrations are not rolled back by reverting an image. If a migration or rollout fails, inspect the admin logs and upstream recovery guidance before rerunning or rolling back. If the task waiter fails, the runner requests task cancellation; confirm the task has stopped before retrying the release.
