import subprocess
import yaml
import time
from get_resources import get_service_pod_resources
from ML import get_action_from_model
from get_current import get_knative_service_settings
from send_requests import run_requests

# -----------------------------------------------------------------------------
# Function: parse_cpu
# Description:
#     Parses a CPU string (e.g., "500m" or "1") and returns the value in millicores.
#     If the string ends with 'm', it's treated as millicores directly. Otherwise,
#     it's assumed to be cores and converted to millicores.
#
# Parameters:
#     cpu_str (str): The CPU string to parse.
#
# Returns:
#     float: The CPU value in millicores.
# -----------------------------------------------------------------------------
def parse_cpu(cpu_str):
    if cpu_str.endswith('m'):
        return float(cpu_str[:-1])
    else:
        return float(cpu_str) * 1000

# -----------------------------------------------------------------------------
# Function: parse_memory
# Description:
#     Parses a memory string (e.g., "256Mi", "1Gi") and returns the value in MiB.
#     It supports units Ki, Mi, Gi, Ti and converts them to MiB. If no unit is found,
#     it assumes the value is already in MiB.
#
# Parameters:
#     mem_str (str): The memory string to parse.
#
# Returns:
#     float: The memory value in MiB.
# -----------------------------------------------------------------------------
def parse_memory(mem_str):
    units = {"Ki": 1/1024, "Mi": 1, "Gi": 1024, "Ti": 1048576}
    for unit in units:
        if mem_str.endswith(unit):
            return float(mem_str[:-len(unit)]) * units[unit]
    return float(mem_str)

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function of the pipeline script. It orchestrates fetching service
#     settings, resource usage, getting action from ML model, and applying
#     scaling actions based on the model's recommendation.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    NAMESPACE = "default"
    SERVICE_NAME = "hello"

    settings = get_knative_service_settings(NAMESPACE, SERVICE_NAME)
    if settings is None:
        print("pipeline.py: Failed to fetch Knative service settings.")
        return

    min_scale, max_scale, cpu_request, memory_request, cpu_limit, memory_limit = settings
    print(f"Initial settings fetched: min_scale={min_scale}, max_scale={max_scale}, "
          f"cpu_request={cpu_request}, memory_request={memory_request}, "
          f"cpu_limit={cpu_limit}, memory_limit={memory_limit}")

    cpu_request_val = parse_cpu(cpu_request)
    memory_request_val = parse_memory(memory_request)
    cpu_limit_val = parse_cpu(cpu_limit)
    memory_limit_val = parse_memory(memory_limit)

    concurrency, latency = run_requests()

    total_cpu_usage, total_memory_usage = get_service_pod_resources(
        namespace=NAMESPACE, service_name=SERVICE_NAME
    )

    if total_cpu_usage is not None and total_memory_usage is not None:
        total_memory_usage_mi = total_memory_usage / (1024 * 1024)
        print(f"pipeline.py: CPU '{SERVICE_NAME}': {total_cpu_usage:.2f} m")
        print(f"pipeline.py: MEM '{SERVICE_NAME}': {total_memory_usage_mi:.2f} Mi")

        num_pods = max_scale
        cpu_per_pod = cpu_request_val
        mem_per_pod = memory_request_val

        print(f"pipeline.py: Number of Pods: {num_pods}, CPU per Pod: {cpu_per_pod}m, Memory per Pod: {mem_per_pod}Mi")

        action = get_action_from_model(
            cpu_usage=total_cpu_usage,
            memory_usage=total_memory_usage_mi,
            concurrency=concurrency,
            latency=latency,
            num_pods=num_pods,
            cpu_per_pod=cpu_per_pod,
            memory_per_pod=mem_per_pod
        )

        if action is None:
            print("pipeline.py: Failed to get action from the ML model.")
            return

        print(f"pipeline.py: Action received from ML.py: {action}")

        if action == 0:
            print("pipeline.py: No action needed.")
            pass
        elif action == 1:
            max_scale += 1
            min_scale = max_scale
            print(f"pipeline.py: Scaling up pods to {max_scale}")
        elif action == 2:
            max_scale = max(1, max_scale - 1)
            min_scale = max_scale
            print(f"pipeline.py: Scaling down pods to {max_scale}")
        elif action == 3:
            cpu_request_val *= 2
            memory_request_val *= 2
            cpu_limit_val *= 2
            memory_limit_val *= 2
            print(f"pipeline.py: Increasing resources per pod to CPU {cpu_request_val}m, Memory {memory_request_val}Mi")
        elif action == 4:
            cpu_request_val = max(100, cpu_request_val / 2)
            memory_request_val = max(128, memory_request_val / 2)
            cpu_limit_val = max(100, cpu_limit_val / 2)
            memory_limit_val = max(128, memory_limit_val / 2)
            print(f"pipeline.py: Decreasing resources per pod to CPU {cpu_request_val}m, Memory {memory_request_val}Mi")
        else:
            print("pipeline.py: Unknown action. No changes made.")
            return

        cpu_request_str = f"{int(cpu_request_val)}m"
        memory_request_str = f"{int(memory_request_val)}Mi"
        cpu_limit_str = f"{int(cpu_limit_val)}m"
        memory_limit_str = f"{int(memory_limit_val)}Mi"

        try:
            subprocess.run([
                "python3", "change_settings.py",
                "--namespace", NAMESPACE,
                "--service-name", SERVICE_NAME,
                "--scale-to-zero-grace-period", "0s",
                "--scale-up-delay", "0s",
                "--scale-down-delay", "0s",
                "--container-concurrency", "1",
                "--min-scale", str(min_scale),
                "--max-scale", str(max_scale),
                "--env-var", "your_env_value",
                "--cpu-request", cpu_request_str,
                "--memory-request", memory_request_str,
                "--cpu-limit", cpu_limit_str,
                "--memory-limit", memory_limit_str,
                "--send-traffic-to-latest"
            ], check=True)
            print("pipeline.py: change_settings.py executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"pipeline.py: Failed to run change_settings.py: {e}")
            if e.stderr:
                print(f"pipeline.py: stderr: {e.stderr}")
    else:
        print("pipeline.py: Failed to get resource usage data.")

if __name__ == "__main__":
    main()