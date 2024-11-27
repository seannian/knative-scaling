import sys
import subprocess

# -----------------------------------------------------------------------------
# Function: send_requests
# Description:
#     Sends requests to a specified service URL for a given duration and concurrency.
# 
# Parameters:
#     service_url (str): The URL of the service to send requests to.
#     duration (int): The duration for which requests are to be sent (in seconds).
#     concurrency (int): The number of concurrent requests to be sent.
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
#     Retrieves the URL of a specified Knative service.
# 
# Parameters:
#     service_name (str): The name of the Knative service.
# 
# Returns:
#     str: The URL of the specified service or None if an error occurs.
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
#     Main function to orchestrate sending requests to a Knative service.
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