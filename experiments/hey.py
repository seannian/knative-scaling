# -----------------------------------------------------------------------------
# Script: send_requests_knative
# Description:
#     Sends a specified number of HTTP requests to a Knative service to test its
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

def send_requests(service_url, total_requests, concurrency):
    print(f"Sending {total_requests} requests to {service_url} with concurrency {concurrency}")
    
    hey_command = [
        "hey",
        "-n", str(total_requests),  # Total number of requests
        "-c", str(concurrency),     # Number of concurrent users
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
    TOTAL_REQUESTS = 5000        # Total number of requests
    CONCURRENCY = 100            # Number of concurrent users

    service_url = get_service_url(SERVICE_NAME)
    if not service_url:
        print("Cannot proceed without a valid service URL.")
        sys.exit(1)
    print(f"Service URL: {service_url}")
    
    send_requests(service_url, TOTAL_REQUESTS, CONCURRENCY)

if __name__ == "__main__":
    main()