-include .env
export

PY_VERSION := $(shell cat .python-version)

.PHONY: build-pyenv install pre-commit-setup test test_cov test_e2e run_frontend run_backend run stop

build-pyenv:
	pyenv install -s ${PY_VERSION}
	poetry env use ${PY_VERSION}

install:
	cd frontend && npm install
	brew install ffmpeg
	poetry install --with fastapi --no-root
	poetry run pre-commit install

run-pre-commit:
	poetry run pre-commit run --all-files

test:
	poetry run pytest --cov --cov-report=term-missing 

test-cov:
	poetry run pytest --cov --cov-report=html --cov-report=xml --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-evals:
	poetry run pytest tests/evals/ --cov=evals --cov-report=html:htmlcov/evals --cov-report=xml --cov-report=term-missing -o addopts=
	@echo "Coverage report generated in htmlcov/evals"

run_frontend:
	cd frontend && npm run dev

run_backend:
	poetry run uvicorn backend.main:app --reload --port 8080

run_worker:
	poetry run python backend/services/queue_service.py

run:
	docker compose up -d --wait

run_watch:
	docker compose up --watch

stop:
	docker compose down


.PHONY: generate_aws_diagram
generate_aws_diagram:
	poetry install --with dev
	poetry run python terraform/diagram_script.py

# Docker

ECR_REPO_NAME=$(APP_NAME)-$(service)
ECR_URL=$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
ECR_REPO_URL=$(ECR_URL)/$(ECR_REPO_NAME)

IMAGE_TAG=$$(git rev-parse HEAD)
IMAGE=$(ECR_REPO_URL):$(IMAGE_TAG)

DOCKER_BUILDER_CONTAINER=$(APP_NAME)


docker_login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_URL)

ifndef cache
	override cache = ./.build-cache
endif

docker_build: ## Build the docker container for the specified service when running in CI/CD
	DOCKER_BUILDKIT=1 docker buildx build --platform linux/amd64 --load --builder=$(DOCKER_BUILDER_CONTAINER) -t $(IMAGE) \
	$(DOCKER_BUILD_ARGS) \
	--cache-to type=local,dest=$(cache) \
	--cache-from type=local,src=$(cache) \
	-f $(service)/Dockerfile .

docker_build_local: ## Build the docker container for the specified service locally
	DOCKER_BUILDKIT=1 docker build --platform=linux/amd64 -t $(IMAGE) -f $(service)/Dockerfile .

docker_push:
	docker push $(IMAGE)

docker_tag_is_present_on_image:
	aws ecr describe-images --repository-name $(repo) --image-ids imageTag=$(IMAGE_TAG) --query 'imageDetails[].imageTags' | jq -e '.[]|any(. == "$(tag)")' >/dev/null

check_docker_tag_exists:
	if ! make docker_tag_is_present_on_image tag=$(IMAGE_TAG) 2>/dev/null; then \
		echo "Error: ECR tag $(IMAGE_TAG) does not exist." && exit 1; \
	fi

docker_update_tag: ## Tag the docker image with the specified tag
	# repo and tag variable are set from git-hub core workflow. example: repo=ecr-repo-name, tag=dev
	if make docker_tag_is_present_on_image 2>/dev/null; then echo "Image already tagged with $(tag)" && exit 0; fi && \
	MANIFEST=$$(aws ecr batch-get-image --repository-name $(repo) --image-ids imageTag=$(IMAGE_TAG) --query 'images[].imageManifest' --output text) && \
	aws ecr put-image --repository-name $(repo) --image-tag $(tag) --image-manifest "$$MANIFEST"

docker_echo:
	echo $($(value))

## Terraform 

ifndef env
override env = default
endif
workspace = $(env)
tf_build_args =-var "image_tag=$(IMAGE_TAG)" -var-file="variables/global.tfvars" -var-file="variables/$(env).tfvars"  
TF_BACKEND_CONFIG=backend.hcl

tf_set_workspace:
	terraform -chdir=terraform/ workspace select $(workspace)

tf_new_workspace:
	terraform -chdir=terraform/ workspace new $(workspace)

tf_set_or_create_workspace:
	make tf_set_workspace || make tf_new_workspace

tf_init_and_set_workspace:
	make tf_init && make tf_set_or_create_workspace

.PHONY: tf_init
tf_init:
	terraform -chdir=./terraform/ init \
		-backend-config=$(TF_BACKEND_CONFIG) \
		-backend-config="dynamodb_table=i-dot-ai-$(env)-dynamo-lock" \
		-reconfigure \

.PHONY: tf_fmt
tf_fmt:
	terraform fmt

.PHONY: tf_plan
tf_plan:
	make tf_init_and_set_workspace && \
	terraform -chdir=./terraform/ plan ${tf_build_args} ${args}

.PHONY: tf_apply
tf_apply:
	make tf_init_and_set_workspace && \
	terraform -chdir=./terraform/ apply ${tf_build_args} ${args}

.PHONY: tf_auto_apply
tf_auto_apply:  ## Auto apply terraform
	make check_docker_tag_exists repo=$(ECR_REPO_NAME)
	make tf_init_and_set_workspace && \
	terraform -chdir=./terraform/ apply  ${tf_build_args} ${args} -auto-approve

## Release app
.PHONY: release
release: 
	chmod +x ./release.sh && ./release.sh $(env)

generate_api_types:
	cd frontend && npm run openapi-ts
