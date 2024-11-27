# -----------------------------------------------------------------------------
# Script: send_resource_data
# Description:
#     Sends resource usage data (CPU usage, memory usage, traffic per second, latency)
#     to a prediction endpoint using an HTTP POST request.
# 
# Parameters:
#     None
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
import requests

data = {
    "cpu_usage": 0.5,
    "memory_usage": 0.7,
    "traffic_per_second": 100,
    "latency": 20
}

response = requests.post("http://localhost:8003/predict", json=data)
print(response.json())