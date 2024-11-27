# Knative Pipeline README

## Overview
You run the pipeline with `python3 pipeline.py`, which connects all components. Note that Knative and hello needs to be set up. Guide on that later.

The pipeline process involves:
1. Fetching the Knative service settings.
2. Retrieving resource usage metrics for the service pods.
3. Sending metrics to an ML model to determine scaling and resource allocation actions.
4. Applying scaling or resource adjustments based on the model's output.