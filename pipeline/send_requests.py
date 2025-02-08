import sys
import subprocess
import re
import os

# -----------------------------------------------------------------------------
# Function: send_requests
# Description:
#     Sends HTTP requests to a specified service URL using the 'hey' load
#     testing tool for a given duration and concurrency. It parses the output
#     of 'hey' to extract requests per second and average latency.
#
# Parameters:
#     service_url (str): The URL of the service to send requests to.
#     duration (int): The duration in seconds for which to send requests.
#     concurrency (int): The number of concurrent requests to send.
#
# Returns:
#     tuple: A tuple containing:
#         - requests_sec (float): Requests per second, extracted from 'hey' output.
#         - average_latency (float): Average latency in seconds, extracted from 'hey' output.
#         Returns (None, None) if there is an error or parsing fails.
# -----------------------------------------------------------------------------
def send_requests(service_url, duration, concurrency):
    print(f"Sending requests to {service_url} for {duration} seconds with concurrency {concurrency}")

    duration_str = f"{duration}s"
    hey_command = [
        "hey",
        "-z", duration_str,
        "-c", str(concurrency),
        service_url
    ]

    try:
        output = subprocess.check_output(hey_command, stderr=subprocess.STDOUT, text=True)
        print("hey output:")
        print(output)

        requests_sec = None
        average_latency = None

        for line in output.splitlines():
            if "Requests/sec:" in line:
                match = re.search(r"Requests/sec:\s+([0-9.]+)", line)
                if match:
                    requests_sec = float(match.group(1))
            elif "Average:" in line:
                match = re.search(r"Average:\s+([0-9.]+)\s+secs", line)
                if match:
                    average_latency = float(match.group(1))

        if requests_sec is None or average_latency is None:
            print("Failed to parse 'hey' output for Requests/sec or Average latency.")
            return (None, None)

        return (requests_sec, average_latency)

    except subprocess.CalledProcessError as e:
        print(f"Error running hey: {e}")
        print(e.output)
        return (None, None)

    print("Finished sending requests.")

# -----------------------------------------------------------------------------
# Function: get_service_url
# Description:
#     Retrieves the URL of a Knative service using the 'kn service describe'
#     command. It extracts the URL from the command's output.
#
# Parameters:
#     service_name (str): The name of the Knative service.
#
# Returns:
#     str or None: The URL of the Knative service if successful, otherwise None.
# -----------------------------------------------------------------------------
def get_service_url(service_name):
    try:
        url = subprocess.check_output(
            ["kn", "service", "describe", service_name, "-o", "url"],
            text=True
        ).strip()
        return url
    except subprocess.CalledProcessError as e:
        print(f"Error fetching service URL: {e}")
        return None

# -----------------------------------------------------------------------------
# Function: run_requests
# Description:
#     Orchestrates sending requests to a Knative service and retrieving
#     performance metrics (concurrency and latency). It reads service name,
#     request duration, and concurrency from environment variables or defaults.
#
# Parameters:
#     None
#
# Returns:
#     tuple: A tuple containing:
#         - concurrency (int): The concurrency level used for sending requests.
#         - latency (float): The average latency of the requests in seconds.
#         Exits the program if service URL retrieval or request sending fails.
# -----------------------------------------------------------------------------
def run_requests():
    SERVICE_NAME = "hello"
    REQUEST_DURATION = int(os.getenv("REQUEST_DURATION", "15"))
    CONCURRENCY = int(os.getenv("CONCURRENCY", "100"))

    service_url = get_service_url(SERVICE_NAME)
    if not service_url:
        print("Cannot proceed without a valid service URL.")
        sys.exit(1)
    print(f"Service URL: {service_url}")

    traffic_per_second, latency = send_requests(service_url, REQUEST_DURATION, CONCURRENCY)

    if traffic_per_second is None or latency is None:
        print("Failed to retrieve traffic and latency metrics.")
        sys.exit(1)

    return (CONCURRENCY, latency)

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function to execute request sending and metric retrieval.
#     It calls `run_requests` and prints the concurrency and latency.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    concurrency, latency = run_requests()
    print(f"Concurrency: {concurrency}")
    print(f"Latency: {latency}")

if __name__ == "__main__":
    main()