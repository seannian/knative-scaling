# -----------------------------------------------------------------------------
# Function: update_knative_service_all
# Description:
#     Updates a Knative service with new configuration settings, including autoscaling,
#     resource requests, limits, environment variables, and traffic routing.
# 
# Parameters:
#     namespace (str): The Kubernetes namespace of the service.
#     service_name (str): The name of the Knative service to update.
#     scale_to_zero_grace_period (str): Time before scaling the service to zero pods.
#     scale_up_delay (str): Delay before scaling up the service.
#     scale_down_delay (str): Delay before scaling down the service.
#     container_concurrency (int): The maximum concurrency level for the container.
#     min_scale (int): Minimum number of pods to maintain.
#     max_scale (int): Maximum number of pods allowed.
#     env_var (str): Value for the 'TARGET' environment variable.
#     cpu_request (str): Minimum CPU request.
#     memory_request (str): Minimum memory request.
#     cpu_limit (str): Maximum CPU limit.
#     memory_limit (str): Maximum memory limit.
#     send_traffic_to_latest (bool): Whether to route 100% of traffic to the latest revision.
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
import sys
from kubernetes import client, config

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

def main():
    NAMESPACE = "default"
    SERVICE_NAME = "hello"
    SCALE_TO_ZERO_GRACE_PERIOD = "10m"
    SCALE_UP_DELAY = "0s"
    SCALE_DOWN_DELAY = "1m"
    CONTAINER_CONCURRENCY = 1
    MIN_SCALE = 0
    MAX_SCALE = 5
    ENV_VAR = "This is a message"
    CPU_REQUEST = "100m"
    MEMORY_REQUEST = "128Mi"
    CPU_LIMIT = "200m"
    MEMORY_LIMIT = "256Mi"

    update_knative_service_all(
        namespace=NAMESPACE,
        service_name=SERVICE_NAME,
        scale_to_zero_grace_period=SCALE_TO_ZERO_GRACE_PERIOD,
        scale_up_delay=SCALE_UP_DELAY,
        scale_down_delay=SCALE_DOWN_DELAY,
        container_concurrency=CONTAINER_CONCURRENCY,
        min_scale=MIN_SCALE,
        max_scale=MAX_SCALE,
        env_var=ENV_VAR,
        cpu_request=CPU_REQUEST,
        memory_request=MEMORY_REQUEST,
        cpu_limit=CPU_LIMIT,
        memory_limit=MEMORY_LIMIT,
        send_traffic_to_latest=True
    )

if __name__ == "__main__":
    main()