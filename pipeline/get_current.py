import subprocess
import yaml

# -----------------------------------------------------------------------------
# Function: get_knative_service_settings
# Description:
#     Retrieves the autoscaling and resource settings for a Knative service
#     using kubectl. It extracts min-scale, max-scale from annotations, and
#     CPU/Memory requests and limits from the container resources.
#
# Parameters:
#     namespace (str): Kubernetes namespace where the service is located.
#     service_name (str): Name of the Knative service.
#
# Returns:
#     tuple: A tuple containing:
#         - min_scale (int): Minimum number of pods.
#         - max_scale (int): Maximum number of pods.
#         - cpu_request (str): CPU request for the container.
#         - memory_request (str): Memory request for the container.
#         - cpu_limit (str): CPU limit for the container.
#         - memory_limit (str): Memory limit for the container.
#         Returns default values (1, 1, '200m', '256Mi', '200m', '256Mi') in case of failure.
# -----------------------------------------------------------------------------
def get_knative_service_settings(namespace, service_name):
    try:
        # Run kubectl command to get the Knative service YAML configuration
        result = subprocess.run([
            "kubectl", "get", "ksvc", service_name,
            "-n", namespace,
            "-o", "yaml"
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        service_yaml = yaml.safe_load(result.stdout)

        # Extract min-scale and max-scale from annotations
        annotations = service_yaml['spec']['template']['metadata'].get('annotations', {})
        min_scale = int(annotations.get('autoscaling.knative.dev/min-scale', 1))
        max_scale = int(annotations.get('autoscaling.knative.dev/max-scale', 1))

        # Extract resource requests and limits
        containers = service_yaml['spec']['template']['spec']['containers']
        resources = containers[0].get('resources', {})
        requests = resources.get('requests', {})
        limits = resources.get('limits', {})

        cpu_request = requests.get('cpu', '200m')
        memory_request = requests.get('memory', '256Mi')
        cpu_limit = limits.get('cpu', '200m')
        memory_limit = limits.get('memory', '256Mi')

        return min_scale, max_scale, cpu_request, memory_request, cpu_limit, memory_limit

    except subprocess.CalledProcessError as e:
        print(f"Failed to get service settings: {e.stderr}")
        # Return default values in case of failure
        return 1, 1, '200m', '256Mi', '200m', '256Mi'