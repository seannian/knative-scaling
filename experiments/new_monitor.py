# -----------------------------------------------------------------------------
# Script: monitor_pod_scaling
# Description:
#     Monitors and logs pod scaling events for a specified Knative service within
#     a Kubernetes namespace. The script uses Kubernetes API to watch pod events,
#     logs resource usage, and stores logs in a file upon interruption.
# 
# Parameters:
#     None
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
import sys
import time
import datetime
import os
import logging
import threading
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

# -----------------------------------------------------------------------------
# Class: ListHandler
# Description:
#     A custom logging handler that stores log messages in a list.
#
# Attributes:
#     log_messages (list): A list to store formatted log messages.
# -----------------------------------------------------------------------------
class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_messages = []

    def emit(self, record):
        self.log_messages.append(self.format(record))

# -----------------------------------------------------------------------------
# Function: setup_logging
# Description:
#     Configures the logging system to capture log messages.
#     It sets up a custom ListHandler to store logs in memory and a StreamHandler
#     to output logs to the console.
#
# Returns:
#     ListHandler: The custom handler storing log messages.
# -----------------------------------------------------------------------------
def setup_logging():
    log_directory = "./logs"
    os.makedirs(log_directory, exist_ok=True)  # Ensure the logs directory exists

    list_handler = ListHandler()
    list_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    list_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[list_handler, console_handler]
    )

    logging.info("Logging is set up. Logs will be stored upon interruption.")
    return list_handler

# -----------------------------------------------------------------------------
# Function: format_timedelta
# Description:
#     Formats a `timedelta` object into a human-readable string.
#     The format follows 'XhYm' for hours and minutes, 'XmYs' for minutes and seconds,
#     or 'Xs' for seconds, depending on the duration.
#
# Parameters:
#     td (datetime.timedelta): The timedelta object representing the duration to format.
#
# Returns:
#     str: A human-readable string representing the formatted duration.
# -----------------------------------------------------------------------------
def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m{seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h{minutes}m"

# -----------------------------------------------------------------------------
# Function: parse_cpu_usage
# Description:
#     Parses a CPU usage string and converts it to millicores.
#
# Parameters:
#     cpu_str (str): The CPU usage string.
#
# Returns:
#     float: The CPU usage in millicores.
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
#     float: The memory usage in bytes.
# -----------------------------------------------------------------------------
def parse_memory_usage(memory_str):
    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
             'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}
    for unit, factor in units.items():
        if memory_str.endswith(unit):
            value = float(memory_str[:-len(unit)]) * factor
            return value
    return float(memory_str)

# -----------------------------------------------------------------------------
# Function: get_service_pod_resources
# Description:
#     Retrieves and logs the resource usage (CPU and memory) of all pods
#     associated with a specific service.
#
# Parameters:
#     namespace (str): The Kubernetes namespace.
#     service_name (str): The name of the service.
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def get_service_pod_resources(namespace, service_name):
    logging.info(f"Getting resource usage for service '{service_name}' in namespace '{namespace}'...")
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        api = client.CustomObjectsApi()

        label_selector = f"serving.knative.dev/service={service_name}"
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        if not pods.items:
            logging.info(f"No pods found for service '{service_name}'.")
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
                logging.info(f"Metrics not available for pod {pod_name}")
                continue

            pod_metrics = pod_metrics_map[pod_name]

            for container in pod_metrics['containers']:
                container_name = container['name']
                cpu_usage = container['usage']['cpu']
                memory_usage = container['usage']['memory']

                cpu_usage_millicores = parse_cpu_usage(cpu_usage)
                memory_usage_bytes = parse_memory_usage(memory_usage)

                logging.info(f"Pod: {pod_name}, Container: {container_name}, CPU Usage: {cpu_usage_millicores:.2f} m, Memory Usage: {memory_usage_bytes / (1024 ** 2):.2f} Mi")

                total_cpu_usage += cpu_usage_millicores
                total_memory_usage += memory_usage_bytes

        logging.info(f"Total CPU Usage for service '{service_name}': {total_cpu_usage:.2f} m")
        logging.info(f"Total Memory Usage for service '{service_name}': {total_memory_usage / (1024 ** 2):.2f} Mi")

    except ApiException as e:
        logging.error(f"Failed to get resource usage: {e}")

# -----------------------------------------------------------------------------
# Function: resource_monitoring
# Description:
#     Monitors resource usage every 15 seconds in a separate thread.
#     It continues until the stop_event is set.
#
# Parameters:
#     namespace (str): The Kubernetes namespace.
#     service_name (str): The name of the service.
#     stop_event (threading.Event): An event to signal the thread to stop.
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def resource_monitoring(namespace, service_name, stop_event):
    while not stop_event.is_set():
        get_service_pod_resources(namespace, service_name)
        stop_event.wait(15)

# -----------------------------------------------------------------------------
# Function: monitor_pod_scaling
# Description:
#     Monitors pod scaling events for a specific Knative service within a Kubernetes namespace.
#     It starts the resource monitoring in a separate thread.
#
# Parameters:
#     namespace (str): The Kubernetes namespace where the service is located.
#     service_name (str): The name of the Knative service to monitor.
#     monitoring_duration (int): The total duration for monitoring in seconds.
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def monitor_pod_scaling(namespace, service_name, monitoring_duration):
    label_selector = f"serving.knative.dev/service={service_name}"
    logging.info("Monitoring pod scaling in namespace '%s' with label selector '%s'...", namespace, label_selector)
    
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        end_time = time.time() + monitoring_duration

        try:
            pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
            current_pods = set(pod.metadata.name for pod in pods.items)
            pod_count = len(current_pods)
            logging.info("Initial Pod Count: %d", pod_count)
        except Exception as e:
            logging.error("Error initializing pod list: %s", e)
            current_pods = set()
            pod_count = 0

        stop_event = threading.Event()
        resource_thread = threading.Thread(target=resource_monitoring, args=(namespace, service_name, stop_event))
        resource_thread.start()

        w = watch.Watch()
        try:
            for event in w.stream(v1.list_namespaced_pod,
                                  namespace=namespace,
                                  label_selector=label_selector,
                                  timeout_seconds=monitoring_duration):
                event_type = event['type']
                pod = event['object']
                pod_name = pod.metadata.name

                current_time = datetime.datetime.now(datetime.timezone.utc)
                creation_time = pod.metadata.creation_timestamp

                if creation_time:
                    pod_age_timedelta = current_time - creation_time
                    pod_age = format_timedelta(pod_age_timedelta)
                else:
                    pod_age = "Unknown"

                if event_type == 'ADDED':
                    if pod_name not in current_pods:
                        current_pods.add(pod_name)
                        pod_count = len(current_pods)
                        logging.info("[Pod Event] %s - Pod: %s, Pod Count: %d, Age: %s",
                                     event_type, pod_name, pod_count, pod_age)
                elif event_type == 'DELETED':
                    current_pods.discard(pod_name)
                    pod_count = len(current_pods)
                    logging.info("[Pod Event] %s - Pod: %s, Pod Count: %d, Age: %s",
                                 event_type, pod_name, pod_count, pod_age)
                elif event_type == 'MODIFIED':
                    status_phase = pod.status.phase
                    if pod.metadata.deletion_timestamp:
                        status_message = "Terminating"
                    else:
                        status_conditions = pod.status.conditions
                        if status_conditions:
                            for condition in status_conditions:
                                if condition.type == "Ready" and condition.status == "False":
                                    status_message = f"Not Ready: {condition.reason}"
                                    break
                            else:
                                status_message = f"Status: {status_phase}"
                        else:
                            status_message = f"Status: {status_phase}"
                    logging.info("[Pod Event] %s - Pod: %s, %s, Age: %s",
                                 event_type, pod_name, status_message, pod_age)
                else:
                    logging.info("[Pod Event] %s - Pod: %s, Age: %s",
                                 event_type, pod_name, pod_age)

                if time.time() >= end_time:
                    w.stop()
                    break

            logging.info("Finished monitoring pod scaling.")
        except Exception as e:
            logging.error("Error watching pod events: %s", e)
        finally:
            stop_event.set()
            resource_thread.join()

    except Exception as e:
        logging.error("Unexpected error in monitor_pod_scaling: %s", e)

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     The main entry point of the script. It sets up logging, defines configuration parameters,
#     and initiates the pod scaling monitoring process for a specified Knative service within a Kubernetes namespace.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    list_handler = setup_logging()

    NAMESPACE = "default"
    SERVICE_NAME = "hello"

    MONITORING_DURATION = 100000

    try:
        monitor_pod_scaling(NAMESPACE, SERVICE_NAME, MONITORING_DURATION)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Stopping monitoring...")
    finally:
        log_messages = list_handler.log_messages

        if log_messages:
            current_date = datetime.datetime.now().strftime("%m_%d_%Y")
            finish_time = datetime.datetime.now().strftime("%I_%M_%S_%p")
            log_filename = f"{current_date}_{finish_time}.log"
            log_path = os.path.join("./logs", log_filename)

            try:
                with open(log_path, "w") as log_file:
                    for message in log_messages:
                        log_file.write(message + "\n")
                print(f"\nLog saved to {log_path}")
            except Exception as e:
                print(f"Failed to write log file: {e}")
        else:
            print("\nNo log messages to save.")

if __name__ == "__main__":
    main()