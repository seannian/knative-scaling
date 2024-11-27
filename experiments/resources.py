# -----------------------------------------------------------------------------
# Function: get_service_pod_resources
# Description:
#     Retrieves and displays resource usage for all pods of a given Knative service
#     within a specified Kubernetes namespace. The function lists each pod's CPU and
#     memory usage, and calculates the total resource usage for the service.
# 
# Parameters:
#     namespace (str): The Kubernetes namespace of the service.
#     service_name (str): The name of the Knative service.
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
import sys
from kubernetes import client, config
from kubernetes.client.rest import ApiException

def get_service_pod_resources(namespace, service_name):
    print(f"Getting resource usage for service '{service_name}' in namespace '{namespace}'...")

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        api = client.CustomObjectsApi()

        label_selector = f"serving.knative.dev/service={service_name}"
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        if not pods.items:
            print(f"No pods found for service '{service_name}'.")
            return

        total_cpu_usage = 0
        total_memory_usage = 0

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

        print(f"\nTotal CPU Usage for service '{service_name}': {total_cpu_usage:.2f} m")
        print(f"Total Memory Usage for service '{service_name}': {total_memory_usage / (1024 ** 2):.2f} Mi")

    except ApiException as e:
        print(f"Failed to get resource usage: {e}")
        sys.exit(1)

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

def parse_memory_usage(memory_str):
    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
             'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}
    for unit, factor in units.items():
        if memory_str.endswith(unit):
            value = float(memory_str[:-len(unit)]) * factor
            return value
    return float(memory_str)

def main():
    NAMESPACE = "default"
    SERVICE_NAME = "hello"

    get_service_pod_resources(namespace=NAMESPACE, service_name=SERVICE_NAME)

if __name__ == "__main__":
    main()