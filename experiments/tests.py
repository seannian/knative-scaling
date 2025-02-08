# -----------------------------------------------------------------------------
# Script: send_requests_knative
# Description:
#     Sends HTTP requests to a Knative service for a specified duration to test its
#     response under load. The script fetches the service URL and uses the 'hey'
#     tool to send concurrent requests, capturing the output.
# 
# Parameters:
#     None
# 
# Returns:
#     None
# -----------------------------------------------------------------------------

import sys
import subprocess

def send_requests(service_url, duration, concurrency):
    print(f"Sending requests to {service_url} for {duration} with concurrency {concurrency}")
    
    hey_command = [
        "hey",
        "-z", duration,          # Duration for the test
        "-c", str(concurrency),  # Number of concurrent users
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

def main():
    SERVICE_NAME = "hello"       # Service name is fixed to "hello"

    # Duration for tests (e.g., 1 minute)
    duration = "1m"
    # Different concurrency levels to test (maximum concurrency is 250)
    concurrency_levels = [5, 10, 20, 30, 40, 50, 75, 100]

    service_url = get_service_url(SERVICE_NAME)
    if not service_url:
        print("Cannot proceed without a valid service URL.")
        sys.exit(1)
    print(f"Service URL: {service_url}")
    
    # Run tests for different concurrency levels
    for concurrency in concurrency_levels:
        print(f"\nStarting test for {duration} with concurrency level: {concurrency}")
        send_requests(service_url, duration, concurrency)

if __name__ == "__main__":
    main()
