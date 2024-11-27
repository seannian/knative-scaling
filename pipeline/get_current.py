import subprocess
import yaml

# -----------------------------------------------------------------------------
# Function: get_knative_service_settings
# Description:
#     Retrieves the scaling and resource settings for a specified Knative service
#     from its YAML configuration.
# 
# Parameters:
#     namespace (str): The namespace in which the Knative service is running.
#     service_name (str): The name of the Knative service.
# 
# Returns:
#     tuple: A tuple containing min-scale, max-scale, CPU request, memory request,
#            CPU limit, and memory limit values.
# -----------------------------------------------------------------------------
def get_knative_service_settings(namespace, service_name):
    try:
        result = subprocess.run([
            "kubectl", "get", "ksvc", service_name,
            "-n", namespace,
            "-o", "yaml"
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        service_yaml = yaml.safe_load(result.stdout)

        annotations = service_yaml['spec']['template']['metadata'].get('annotations', {})
        min_scale = int(annotations.get('autoscaling.knative.dev/min-scale', 1))
        max_scale = int(annotations.get('autoscaling.knative.dev/max-scale', 1))

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
        return 1, 1, '200m', '256Mi', '200m', '256Mi'