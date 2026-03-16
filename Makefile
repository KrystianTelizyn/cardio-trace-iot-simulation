.PHONY: download-physionet import-physionet

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
