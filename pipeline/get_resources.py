import sys
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# -----------------------------------------------------------------------------
# Function: get_service_pod_resources
# Description:
#     Retrieves the CPU and memory resource usage for pods of a specified Knative
#     service in a given namespace.
# 
# Parameters:
#     namespace (str): The namespace in which the Knative service is running.
#     service_name (str): The name of the Knative service.
# 
# Returns:
#     tuple: A tuple containing average CPU usage (millicores) and memory usage (MiB).
# -----------------------------------------------------------------------------
def get_service_pod_resources(namespace, service_name):
    print(f"Getting resource usage for service '{service_name}' in namespace '{namespace}'...")

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        api = client.CustomObjectsApi()

        label_selector = f"serving.knative.dev/service={service_name}"
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        if not pods.items:
            print(f"No pods found for service '{service_name}'. Returning 0 for CPU and memory usage.")
            return 0, 0

        total_cpu_usage = 0
        total_memory_usage = 0
        pod_count = len(pods.items)

        group = 'metrics.k8s.io'
        version = 'v1beta1'
        plural = 'pods'
        pod_metrics_list = api.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        )

        pod_metrics_map = {item['metadata']['name']: item for item in pod_metrics_list['items']}

        for pod in pods.items:
            pod_name = pod.metadata.name

            if pod_name not in pod_metrics_map:
                print(f"Metrics not available for pod {pod_name}")
                continue

            pod_metrics = pod_metrics_map[pod_name]

            for container in pod_metrics['containers']:
                container_name = container['name']
                cpu_usage = container['usage']['cpu']
                memory_usage = container['usage']['memory']

                cpu_usage_millicores = parse_cpu_usage(cpu_usage)
                memory_usage_bytes = parse_memory_usage(memory_usage)

                print(f"Pod: {pod_name}, Container: {container_name}, CPU Usage: {cpu_usage_millicores:.2f} m, Memory Usage: {memory_usage_bytes / (1024 ** 2):.2f} Mi")

                total_cpu_usage += cpu_usage_millicores
                total_memory_usage += memory_usage_bytes

        avg_cpu_usage = total_cpu_usage / pod_count if pod_count > 0 else 0
        avg_memory_usage = total_memory_usage / pod_count if pod_count > 0 else 0

        print(f"\nTotal CPU Usage for service '{service_name}': {total_cpu_usage:.2f} m")
        print(f"Total Memory Usage for service '{service_name}': {total_memory_usage / (1024 ** 2):.2f} Mi")
        print(f"\nAverage CPU Usage for service '{service_name}': {avg_cpu_usage:.2f} m")
        print(f"Average Memory Usage for service '{service_name}': {avg_memory_usage / (1024 ** 2):.2f} Mi")

        return avg_cpu_usage, avg_memory_usage

    except ApiException as e:
        print(f"Failed to get resource usage: {e}")
        sys.exit(1)

# -----------------------------------------------------------------------------
# Function: parse_cpu_usage
# Description:
#     Parses a CPU usage string and converts it to millicores.
# 
# Parameters:
#     cpu_str (str): The CPU usage string.
# 
# Returns:
#     float: The CPU usage value in millicores.
# -----------------------------------------------------------------------------
def parse_cpu_usage(cpu_str):
    if cpu_str.endswith('n'):
        value = float(cpu_str[:-1]) / 1e6
    elif cpu_str.endswith('u'):
        value = float(cpu_str[:-1]) / 1e3
    elif cpu_str.endswith('m'):
        value = float(cpu_str[:-1])
    else:
        value = float(cpu_str) * 1000
    return value

# -----------------------------------------------------------------------------
# Function: parse_memory_usage
# Description:
#     Parses a memory usage string and converts it to bytes.
# 
# Parameters:
#     memory_str (str): The memory usage string.
# 
# Returns:
#     float: The memory usage value in bytes.
# -----------------------------------------------------------------------------
def parse_memory_usage(memory_str):
    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
             'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}
    for unit, factor in units.items():
        if memory_str.endswith(unit):
            value = float(memory_str[:-len(unit)]) * factor
            return value
    return float(memory_str)