# Release the application and Temporal separately

```console
make release env=dev                  # frontend, backend and application worker
make release-temporal-server env=dev  # build and release only the Temporal server
```

Application releases use `terraform/`; server releases use `terraform-temporal/`, with separate state. The server image is built only during a server release. Both commands release the current **committed** revision, not uncommitted files. Terraform 1.7 or newer is required.

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
