import subprocess
import os
import sys
from datetime import datetime

# -----------------------------------------------------------------------------
# Function: get_knative_service_yaml
# Description:
#     Retrieves the YAML configuration of a Knative service using kubectl
#     and saves it to a file. The output filename includes the current
#     date and time. It also handles directory creation and errors.
#
# Parameters:
#     service_name (str): The name of the Knative service to fetch the YAML for.
#     output_directory (str): The directory where the YAML file will be saved.
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def get_knative_service_yaml(service_name, output_directory):
    now = datetime.now()
    filename = now.strftime("%m-%d-%Y_%I-%M%p") + ".yaml"
    cmd = ["kubectl", "get", "ksvc", service_name, "-o", "yaml"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            print(f"Created directory: {output_directory}")
        elif not os.path.isdir(output_directory):
            print(f"Error: The path '{output_directory}' exists and is not a directory.")
            sys.exit(1)

        output_path = os.path.join(output_directory, filename)

        with open(output_path, 'w') as file:
            file.write(result.stdout)

        print(f"YAML configuration saved to {output_path}")

    except subprocess.CalledProcessError as e:
        print("Error executing kubectl command:", e)
        print("stderr:", e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("kubectl command not found. Please ensure kubectl is installed and in your PATH.")
        sys.exit(1)
    except Exception as e:
        print("An unexpected error occurred:", e)
        sys.exit(1)

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function to execute the script. It defines the service name and
#     output directory and then calls `get_knative_service_yaml` to fetch
#     and save the service's YAML configuration.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    service_name = "hello"
    output_directory = "/Users/seannian/Desktop/180H/yaml"

    get_knative_service_yaml(service_name, output_directory)

if __name__ == "__main__":
    main()