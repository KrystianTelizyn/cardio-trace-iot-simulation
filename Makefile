.PHONY: download-physionet import-physionet docker-build docker-run compose-up compose-down compose-logs compose-ps

IMAGE ?= cardio-trace-iot-sim:dev
ENV_FILE ?= .env
COMPOSE_FILE ?= docker-compose.dev.yml

# PhysioNet dataset URL and target directory
PHYSIONET_ZIP_URL := https://physionet.org/content/rr-interval-healthy-subjects/get-zip/1.0.0/
RR_DATA_DIR := data/rr-interval-healthy-subjects

# Download PhysioNet RR interval records (zip) and extract into data/rr-interval-healthy-subjects
download-physionet:
	@rm -f rr-interval-healthy-subjects.zip
	wget -O rr-interval-healthy-subjects.zip $(PHYSIONET_ZIP_URL)
	@mkdir -p data
	@rm -rf $(RR_DATA_DIR)
	@rm -rf data/rr-interval-time-series-from-healthy-subjects-1.0.0
	unzip -o rr-interval-healthy-subjects.zip -d data
	@if [ -d data/rr-interval-time-series-from-healthy-subjects-1.0.0 ]; then mv data/rr-interval-time-series-from-healthy-subjects-1.0.0 $(RR_DATA_DIR); fi

# Run import script to load PhysioNet data into the repository
import-physionet:
	python -m scripts.import_rr_interval_healthy_subjects

# Build the local Docker image
docker-build:
	docker build -t $(IMAGE) .

# Run API container with environment loaded from .env
docker-run:
	@mkdir -p data
	docker run --rm -p 8000:8000 \
		--env-file $(ENV_FILE) \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/tests:/app/tests:ro \
		$(IMAGE)

# Start the development stack (API + broker)
compose-up:
	@mkdir -p data
	docker compose -f $(COMPOSE_FILE) up --build

# Stop and remove development stack containers/networks
compose-down:
	docker compose -f $(COMPOSE_FILE) down

# Follow development stack logs
compose-logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# Show development stack container status
compose-ps:
	docker compose -f $(COMPOSE_FILE) ps
