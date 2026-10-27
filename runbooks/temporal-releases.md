# Release the application and Temporal separately

```console
make release env=dev                  # frontend, backend and application worker
make release-temporal-server env=dev  # build and release only the Temporal server
```

Application releases use `terraform/`; server releases use `terraform-temporal/`, with separate state. The server image is built only during a server release. Both commands release the current **committed** revision, not uncommitted files. Terraform 1.7 or newer is required.

## What a server release does

Every explicit server release builds `minute-temporal` and `minute-temporal-admin` at the version in `temporal/version.env`, then:

1. Provisions the database and one-off admin task definition without updating the running server.
2. Runs the admin task to initialise empty databases or apply missing schema migrations to both databases. An up-to-date schema is a no-op; any failure stops the release before server rollout.
3. Deploys the server and waits for ECS readiness.
4. Runs a namespace task, creating `default` only if it is absent. Failure marks the release unsuccessful.

There is no continuously running admin service. Server restarts do not run migrations. The server uses `temporal_runtime`, a non-owner database user; only the schema task receives master credentials. The release's targeted Terraform apply is restricted to admin-task provisioning; the subsequent apply covers the whole server stack.

Provision the `minute-temporal-admin` ECR repository in the platform alongside `minute-temporal` before the first release. The deployment role/permissions boundary must permit the admin task's IAM role, `ecs:RunTask`, task inspection and `iam:PassRole`. Task logs are in `/ecs/i-dot-ai-<env>-minute-temporal-admin`.

For local development, Compose runs the same schema and namespace steps as one-off services. Start through `make run` so both images receive `temporal/version.env`.

## First release of the split configuration to dev

Dev is disposable, so recreate Temporal rather than transfer its state. **This deletes dev's Temporal database and workflow history, not the application's database.** Do not run another release during cleanup, and do not submit recordings until the new server is healthy.

### 1. Commit and push the new configuration

Include the new `terraform-temporal/` directory, application outputs, release changes and tests, and the deletion of `terraform/temporal.tf`. Wait for the application image builds and checks to pass.

### 2. Release the application and let Terraform clean up

```console
make release env=dev
```

Wait for **release-infrastructure** in GitHub Actions to finish successfully. On this first release, Terraform deletes the old Temporal resources because they are no longer in the application configuration. It also publishes the networking outputs the standalone server needs. The application database stays in the application configuration and is not removed.

If cleanup fails, or the old Temporal resources were previously forgotten from application state, stop and investigate before creating same-named replacements. Transcription will be unavailable until the server is created.

### 3. Release the standalone Temporal server

```console
make release-temporal-server env=dev
```

Wait for **release-infrastructure** to finish successfully. Confirm the Temporal ECS service is healthy and the application worker is running, then test an upload. If state access is denied, the deployment role needs access to the new `minute-temporal/terraform.tfstate` key under the dev workspace prefix.

## Subsequent releases

Release application changes with `make release env=dev`; Temporal stays running. Release changes to the server image/configuration with `make release-temporal-server env=dev`; application containers stay unchanged. Check Temporal's upstream upgrade requirements before changing its version.

Preprod has no old Temporal deployment: release the application first, then run both commands with `env=preprod`. For production, use **release-infrastructure** manually on `main`, selecting environment `prod` and releasing component `app` first, then `temporal-server`. No state migration is needed for either environment.

## Before production and version upgrades

Rehearse in preprod with existing workflows: release, restart the server, and confirm the data survives. Production server releases require checking **server_upgrade_reviewed** in the manual workflow. Review Temporal's supported version sequence and schema compatibility before ticking it; this acknowledgement is not an automatic compatibility check.

Aurora has deletion protection outside dev and 35-day automated backups. Before an upgrade, verify backups and recovery access, and take a manual snapshot when required by the upgrade plan. Restore to a separate cluster from a known-good snapshot or point-in-time, confirm its workflow data, and switch endpoints only after verification. Do not delete the original cluster until recovery is validated. The shared RDS module skips final snapshots on deletion, so deletion protection is not a substitute for backups.

Schema migrations are not rolled back by reverting an image. If a migration or rollout fails, inspect the admin logs and upstream recovery guidance before rerunning or rolling back. If the task waiter fails, the runner requests task cancellation; confirm the task has stopped before retrying the release.
