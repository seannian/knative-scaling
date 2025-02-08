import requests

# -----------------------------------------------------------------------------
# Function: get_action_from_model
# Description:
#     Sends a prediction request to the ML model and returns the recommended action.
#
# Parameters:
#     cpu_usage (float): The CPU usage value in millicores (e.g., 500.0 for 500m).
#     memory_usage (float): The memory usage value in MiB.
#     concurrency (int): The number of requests per second.
#     latency (float): The latency in milliseconds.
#     num_pods (int): Current number of pods running.
#     cpu_per_pod (float): CPU allocated per pod in millicores.
#     memory_per_pod (float): Memory allocated per pod in MiB.
#
# Returns:
#     int: The action recommended by the ML model.
# -----------------------------------------------------------------------------
def get_action_from_model(cpu_usage, memory_usage, concurrency, latency, num_pods, cpu_per_pod, memory_per_pod):
    print(f"ML.py: cpu_usage={cpu_usage}, memory_usage={memory_usage}, concurrency={concurrency}, latency={latency}, num_pods={num_pods}, cpu_per_pod={cpu_per_pod}, memory_per_pod={memory_per_pod}")

    data = {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "concurrency": concurrency,
        "latency": latency,
        "num_pods": num_pods,
        "cpu_per_pod": cpu_per_pod,
        "memory_per_pod": memory_per_pod
    }

    try:
        response = requests.post("http://localhost:8003/predict", json=data)
        response.raise_for_status()
        result = response.json()
        action = result.get('action')
        if action is None:
            raise ValueError("Action not found in the response.")
        return action
    except requests.exceptions.HTTPError as http_err:
        print(f"ML.py: HTTP error occurred: {http_err} - Response Body: {response.text}")
    except Exception as e:
        print(f"ML.py: Failed to get action from model: {e}")
    return None

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function for standalone execution of ML.py.
#     Parses command line arguments for model parameters and prints the action.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import argparse

    def main():
        parser = argparse.ArgumentParser(description='ML.py: Send a prediction request with custom parameters.')
        parser.add_argument('--cpu-usage', type=float, required=True, help='CPU usage value in millicores (e.g., 500.0 for 500m)')
        parser.add_argument('--memory-usage', type=float, required=True, help='Memory usage value in MiB (e.g., 256.0)')
        parser.add_argument('--concurrency', type=int, required=True, help='Traffic per second value (e.g., 100)')
        parser.add_argument('--latency', type=float, required=True, help='Latency value in milliseconds (e.g., 20)')
        parser.add_argument('--num-pods', type=int, required=True, help='Current number of pods running (e.g., 3)')
        parser.add_argument('--cpu-per-pod', type=float, required=True, help='CPU allocated per pod in millicores (e.g., 500.0)')
        parser.add_argument('--memory-per-pod', type=float, required=True, help='Memory allocated per pod in MiB (e.g., 256.0)')

        args = parser.parse_args()

        action = get_action_from_model(
            cpu_usage=args.cpu_usage,
            memory_usage=args.memory_usage,
            concurrency=args.concurrency,
            latency=args.latency,
            num_pods=args.num_pods,
            cpu_per_pod=args.cpu_per_pod,
            memory_per_pod=args.memory_per_pod
        )

        if action is not None:
            print(f"{action}")
        else:
            sys.exit(1)

    main()