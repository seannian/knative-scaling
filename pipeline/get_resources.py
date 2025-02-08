import sys
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# -----------------------------------------------------------------------------
# Function: get_service_pod_resources
# Description:
#     Retrieves and calculates the total and average CPU and memory usage
#     for all pods associated with a given Knative service in a specified
#     namespace. It uses the Kubernetes metrics API to fetch resource usage
#     and calculates the total and average consumption.
#
# Parameters:
#     namespace (str): Kubernetes namespace where the service is located.
#     service_name (str): Name of the Knative service.
#
# Returns:
#     tuple: A tuple containing:
#         - total_cpu_usage (float): Total CPU usage in millicores for all pods of the service.
#         - total_memory_usage (float): Total memory usage in bytes for all pods of the service.
#         Returns (0, 0) if no pods are found for the service or if there is an API error.
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

        return total_cpu_usage, total_memory_usage

    except ApiException as e:
        print(f"Failed to get resource usage: {e}")
        sys.exit(1)

# -----------------------------------------------------------------------------
# Function: parse_cpu_usage
# Description:
#     Parses a CPU usage string from Kubernetes metrics API and converts it
#     to millicores. The CPU usage string can be in nano cores (n), micro cores (u),
#     millicores (m), or cores (no unit).
#
# Parameters:
#     cpu_str (str): CPU usage string from Kubernetes metrics API.
#
# Returns:
#     float: CPU usage in millicores.
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
#     Parses a memory usage string from Kubernetes metrics API and converts it
#     to bytes. The memory usage string can be in Ki, Mi, Gi, Ti, K, M, G, T.
#
# Parameters:
#     memory_str (str): Memory usage string from Kubernetes metrics API.
#
# Returns:
#     float: Memory usage in bytes.
# -----------------------------------------------------------------------------
def parse_memory_usage(memory_str):
    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
             'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}
    for unit, factor in units.items():
        if memory_str.endswith(unit):
            value = float(memory_str[:-len(unit)]) * factor
            return value
    return float(memory_str)