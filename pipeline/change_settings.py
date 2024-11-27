import sys
import argparse
from kubernetes import client, config

# -----------------------------------------------------------------------------
# Function: update_knative_service_all
# Description:
#     Updates various settings of a Knative service, including scaling, container
#     concurrency, resource requests, and environment variables.
# 
# Parameters:
#     namespace (str): The namespace of the Knative service.
#     service_name (str): The name of the Knative service.
#     scale_to_zero_grace_period (str): Grace period before scaling to zero.
#     scale_up_delay (str): Delay before scaling up.
#     scale_down_delay (str): Delay before scaling down.
#     container_concurrency (int): Concurrency level for the container.
#     min_scale (int): Minimum number of pods.
#     max_scale (int): Maximum number of pods.
#     env_var (str): Value for the TARGET environment variable.
#     cpu_request (str): CPU request for the container.
#     memory_request (str): Memory request for the container.
#     cpu_limit (str): CPU limit for the container.
#     memory_limit (str): Memory limit for the container.
#     send_traffic_to_latest (bool): Whether to send all traffic to the latest revision.
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
def update_knative_service_all(namespace, service_name,
                               scale_to_zero_grace_period,
                               scale_up_delay,
                               scale_down_delay,
                               container_concurrency,
                               min_scale,
                               max_scale,
                               env_var,
                               cpu_request,
                               memory_request,
                               cpu_limit,
                               memory_limit,
                               send_traffic_to_latest=True):
    print(f"Updating service '{service_name}' in namespace '{namespace}'...")

    try:
        config.load_kube_config()
        api = client.CustomObjectsApi()
        group = 'serving.knative.dev'
        version = 'v1'
        plural = 'services'

        service = api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=service_name
        )

        existing_containers = service['spec']['template']['spec'].get('containers', [])
        if not existing_containers:
            raise Exception("No containers found in the existing service.")

        existing_container = existing_containers[0]
        container_name = existing_container.get('name', 'user-container')
        image = existing_container.get('image')
        if not image:
            raise Exception("No image found in the existing container.")

        annotations = {
            'autoscaling.knative.dev/scale-to-zero-grace-period': scale_to_zero_grace_period,
            'autoscaling.knative.dev/scale-up-delay': scale_up_delay,
            'autoscaling.knative.dev/scale-down-delay': scale_down_delay,
            'autoscaling.knative.dev/min-scale': str(min_scale),
            'autoscaling.knative.dev/max-scale': str(max_scale)
        }

        env_vars = existing_container.get('env', [])
        env_var_updated = False
        for env in env_vars:
            if env['name'] == 'TARGET':
                env['value'] = env_var
                env_var_updated = True
                break
        if not env_var_updated:
            env_vars.append({'name': 'TARGET', 'value': env_var})

        container_spec = {
            'containerConcurrency': container_concurrency,
            'containers': [{
                'name': container_name,
                'image': image,
                'env': env_vars,
                'resources': {
                    'requests': {
                        'cpu': cpu_request,
                        'memory': memory_request
                    },
                    'limits': {
                        'cpu': cpu_limit,
                        'memory': memory_limit
                    }
                }
            }]
        }

        patch_body = {
            'spec': {
                'template': {
                    'metadata': {
                        'annotations': annotations
                    },
                    'spec': container_spec
                }
            }
        }

        if send_traffic_to_latest:
            patch_body['spec']['traffic'] = [{'latestRevision': True, 'percent': 100}]

        api.patch_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=service_name,
            body=patch_body
        )
        print(f"Service '{service_name}' updated successfully.")
    except Exception as e:
        print(f"Failed to update service: {e}")
        sys.exit(1)

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function to parse arguments and update a Knative service.
# 
# Parameters:
#     None
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Update a Knative service with custom parameters.')
    parser.add_argument('--namespace', type=str, required=True, help='Namespace of the Knative service')
    parser.add_argument('--service-name', type=str, required=True, help='Name of the Knative service')
    parser.add_argument('--scale-to-zero-grace-period', type=str, required=True, help='Time before scaling to zero (e.g., 10m)')
    parser.add_argument('--scale-up-delay', type=str, required=True, help='Delay before scaling up (e.g., 0s)')
    parser.add_argument('--scale-down-delay', type=str, required=True, help='Delay before scaling down (e.g., 1m)')
    parser.add_argument('--container-concurrency', type=int, required=True, help='Concurrency level for the container')
    parser.add_argument('--min-scale', type=int, required=True, help='Minimum number of pods')
    parser.add_argument('--max-scale', type=int, required=True, help='Maximum number of pods')
    parser.add_argument('--env-var', type=str, required=True, help='Value for the TARGET environment variable')
    parser.add_argument('--cpu-request', type=str, required=True, help='CPU request for the container (e.g., 100m)')
    parser.add_argument('--memory-request', type=str, required=True, help='Memory request for the container (e.g., 128Mi)')
    parser.add_argument('--cpu-limit', type=str, required=True, help='CPU limit for the container (e.g., 200m)')
    parser.add_argument('--memory-limit', type=str, required=True, help='Memory limit for the container (e.g., 256Mi)')
    parser.add_argument('--send-traffic-to-latest', action='store_true', help='Send 100% traffic to the latest revision')

    args = parser.parse_args()

    update_knative_service_all(
        namespace=args.namespace,
        service_name=args.service_name,
        scale_to_zero_grace_period=args.scale_to_zero_grace_period,
        scale_up_delay=args.scale_up_delay,
        scale_down_delay=args.scale_down_delay,
        container_concurrency=args.container_concurrency,
        min_scale=args.min_scale,
        max_scale=args.max_scale,
        env_var=args.env_var,
        cpu_request=args.cpu_request,
        memory_request=args.memory_request,
        cpu_limit=args.cpu_limit,
        memory_limit=args.memory_limit,
        send_traffic_to_latest=args.send_traffic_to_latest
    )

if __name__ == "__main__":
    main()