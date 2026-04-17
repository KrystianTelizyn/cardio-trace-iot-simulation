.PHONY: help login download-physionet import-physionet compose-up compose-down compose-logs compose-ps build-image tag-image push-image

IMAGE_NAME := cardio-trace-iot-simulation
IMAGE_TAG := $(or $(IMAGE_TAG),dev)
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
ENV_FILE ?= .env
COMPOSE_FILE ?= docker-compose.dev.yml
AWS_ACCOUNT_ID := 719030484884
AWS_REGION := eu-north-1

# PhysioNet dataset URL and target directory
PHYSIONET_ZIP_URL := https://physionet.org/content/rr-interval-healthy-subjects/get-zip/1.0.0/
RR_DATA_DIR := data/rr-interval-healthy-subjects

.DEFAULT_GOAL := help

help: ## Show available targets
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  %-22s %s\n", $$1, $$2}'
	@echo ""
	@echo "IMAGE_NAME=$(IMAGE_NAME) IMAGE_TAG=$(IMAGE_TAG) IMAGE=$(IMAGE) COMPOSE_FILE=$(COMPOSE_FILE) ENV_FILE=$(ENV_FILE)"

login: ## Login to ECR for Docker image push/pull
	@echo "Initiating ECR login..."
	aws ecr get-login-password --region $(AWS_REGION) \
		| docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

# Download PhysioNet RR interval records (zip) and extract into data/rr-interval-healthy-subjects
download-physionet: ## Download and unpack PhysioNet RR interval dataset
	@rm -f rr-interval-healthy-subjects.zip
	wget -O rr-interval-healthy-subjects.zip $(PHYSIONET_ZIP_URL)
	@mkdir -p data
	@rm -rf $(RR_DATA_DIR)
	@rm -rf data/rr-interval-time-series-from-healthy-subjects-1.0.0
	unzip -o rr-interval-healthy-subjects.zip -d data
	@if [ -d data/rr-interval-time-series-from-healthy-subjects-1.0.0 ]; then mv data/rr-interval-time-series-from-healthy-subjects-1.0.0 $(RR_DATA_DIR); fi

# Run import script to load PhysioNet data into the repository
import-physionet: ## Import downloaded PhysioNet data into local repository
	python -m scripts.import_rr_interval_healthy_subjects


build-image: ## Build IoT simulation Docker image (alias)
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

tag-image: ## Tag IoT simulation Docker image for ECR
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(IMAGE_NAME):$(IMAGE_TAG)

push-image: ## Push IoT simulation Docker image to ECR
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(IMAGE_NAME):$(IMAGE_TAG)

# Start the development stack (API + broker)
compose-up: ## Start development stack (API + broker)
	@mkdir -p data
	docker compose -f $(COMPOSE_FILE) up --build

# Stop and remove development stack containers/networks
compose-down: ## Stop development stack
	docker compose -f $(COMPOSE_FILE) down

# Follow development stack logs
compose-logs: ## Tail development stack logs
	docker compose -f $(COMPOSE_FILE) logs -f

# Show development stack container status
compose-ps: ## Show development stack containers
	docker compose -f $(COMPOSE_FILE) ps
