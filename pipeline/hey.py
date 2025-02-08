import sys
import subprocess

# -----------------------------------------------------------------------------
# Function: send_requests
# Description:
#     Sends HTTP requests to a specified service URL using the 'hey' load
#     testing tool. It runs 'hey' for a given duration with a specified
#     concurrency level and prints the output.
#
# Parameters:
#     service_url (str): The URL of the service to send requests to.
#     duration (int): The duration in seconds for which to send requests.
#     concurrency (int): The number of concurrent requests to send.
#
# Returns:
#     None
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
    except subprocess.CalledProcessError as e:
        print(f"Error running hey: {e}")
        print(e.output)

    print("Finished sending requests.")

# -----------------------------------------------------------------------------
# Function: get_service_url
# Description:
#     Retrieves the URL of a Knative service using the 'kn service describe'
#     command. It extracts the URL from the command output.
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
# Function: main
# Description:
#     Main function of the script. It sets the service name, request duration,
#     and concurrency level. It then retrieves the service URL and calls
#     `send_requests` to initiate load testing.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    SERVICE_NAME = "hello"
    REQUEST_DURATION = 5
    CONCURRENCY = 100

    service_url = get_service_url(SERVICE_NAME)
    if not service_url:
        print("Cannot proceed without a valid service URL.")
        sys.exit(1)
    print(f"Service URL: {service_url}")

    send_requests(service_url, REQUEST_DURATION, CONCURRENCY)

if __name__ == "__main__":
    main()