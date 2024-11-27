import sys
import subprocess
import re

# -----------------------------------------------------------------------------
# Function: send_requests
# Description:
#     Sends requests to a given service URL for a specified duration with a given
#     concurrency level. Uses the 'hey' tool to send requests and parse the output
#     for Requests/sec and Average latency.
#
# Parameters:
#     service_url (str): The URL of the service to send requests to.
#     duration (int): The duration for which to send requests, in seconds.
#     concurrency (int): The number of concurrent users to simulate.
#
# Returns:
#     tuple: A tuple containing (requests per second, average latency).
# -----------------------------------------------------------------------------
def send_requests(service_url, duration, concurrency):
    print(f"Sending requests to {service_url} for {duration} seconds with concurrency {concurrency}")
    
    duration_str = f"{duration}s"  # Convert duration to a string format accepted by 'hey'
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
        
        # Parse the 'hey' output to extract Requests/sec and Average latency
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
#     Fetches the URL for a given Knative service by using the 'kn' command-line tool.
#
# Parameters:
#     service_name (str): The name of the service for which to retrieve the URL.
#
# Returns:
#     str: The URL of the service, or None if the URL could not be retrieved.
# -----------------------------------------------------------------------------
def get_service_url(service_name):
    try:
        # Execute the kn service describe command to get the service URL in text format
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
#     Runs the request-sending process by fetching the service URL and sending
#     requests for a specified duration and concurrency level.
#
# Returns:
#     tuple: A tuple containing (traffic per second, average latency).
# -----------------------------------------------------------------------------
def run_requests():
    SERVICE_NAME = "hello"   # Service name
    REQUEST_DURATION = 5     # Duration in seconds
    CONCURRENCY = 100        # Number of concurrent users

    # Grab service URL
    service_url = get_service_url(SERVICE_NAME)
    if not service_url:
        print("Cannot proceed without a valid service URL.")
        sys.exit(1)
    print(f"Service URL: {service_url}")
    
    traffic_per_second, latency = send_requests(service_url, REQUEST_DURATION, CONCURRENCY)
    
    if traffic_per_second is None or latency is None:
        print("Failed to retrieve traffic and latency metrics.")
        sys.exit(1)
    
    return (traffic_per_second, latency)

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function to execute the workflow of fetching the service URL,
#     sending requests, and printing the resulting traffic and latency metrics.
# -----------------------------------------------------------------------------
def main():
    traffic_per_second, latency = run_requests()
    print(f"Traffic per second: {traffic_per_second}")
    print(f"Latency: {latency}")

if __name__ == "__main__":
    main()