# Knative Pipeline README

## Model

The model is located in the model folder.

## Experiments

Old data is found in CSVs

1. Manually monitor the cluster using new_monitor.py
2. Manually apply yaml files by modifying hello-service.yaml
3. Run tests using tests.py

## Pipeline
The pipeline is intended to automatically apply settings automatically to the knative cluster. Run pipeline.py to start. Note that:
1. A ML service defined in application must be run on port 8003
2. It is hard coded to look for service "hello"

The pipeline process involves:
1. Fetching the Knative service settings.
2. Retrieving resource usage metrics for the service pods.
3. Sending metrics to an ML model to determine scaling and resource allocation actions.
4. Applying scaling or resource adjustments based on the model's output.