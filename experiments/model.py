# -----------------------------------------------------------------------------
# Class: KubernetesEnv
# Description:
#     Custom OpenAI Gym environment for simulating Kubernetes pod scaling and resource
#     management. The environment provides discrete actions for scaling pods and adjusting
#     resources, and simulates the impact on traffic, CPU, memory usage, and latency.
# 
# Parameters:
#     None
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from stable_baselines3 import PPO, DQN
import math
from gymnasium.wrappers import NormalizeObservation

class KubernetesEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(KubernetesEnv, self).__init__()

        # Define action space: 
        # 0 = Do nothing
        # 1 = Scale Up Pods
        # 2 = Scale Down Pods
        # 3 = Increase Resources per Pod
        # 4 = Decrease Resources per Pod
        self.action_space = spaces.Discrete(5)

        # Set maximum values for dynamic variables
        self.MAX_PODS = 100
        self.MAX_CPU_PER_POD = 1000  # Adjust as needed
        self.MAX_MEM_PER_POD = 256  # Adjust as needed

        # Define observation space: 
        # [CPU Usage (%), Memory Usage (%), Traffic per Second, Latency (ms), Number of Pods, CPU per Pod, Memory per Pod]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 1, 100, 128], dtype=np.float32),
            high=np.array([100, 100, 10000, 1000, self.MAX_PODS, self.MAX_CPU_PER_POD, self.MAX_MEM_PER_POD], dtype=np.float32),
            dtype=np.float32
        )

        # Initial dynamic variables
        self.num_pods = 1
        self.cpu_per_pod = 200   
        self.memory_per_pod = 64  

        # Initial State:
        # CPU Usage = 10%
        # Memory Usage = 10%
        # Requests = 0
        # Latency = 100ms
        self.state = np.array([10, 10, 0, 100, self.num_pods, self.cpu_per_pod, self.memory_per_pod], dtype=np.float32) 
        self.max_steps = 100
        self.current_step = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)
        else:
            # Default seed is 42
            np.random.seed(42)

        self.num_pods = 1
        self.cpu_per_pod = 200   
        self.memory_per_pod = 64  

        self.state = np.array([10, 10, 0, 100, self.num_pods, self.cpu_per_pod, self.memory_per_pod], dtype=np.float32)
        self.max_steps = 100
        self.current_step = 0

        return self.state, {}

    def step(self, action):
        self.current_step += 1

        if action == 0:
            # Do nothing
            pass
        elif action == 1:
            # Scale up pods
            self.num_pods = min(self.MAX_PODS, self.num_pods + 1)
        elif action == 2:
            # Scale down pods
            self.num_pods = max(1, self.num_pods - 1)  # Ensure at least one pod
        elif action == 3:
            # Increase resources per pod
            self.cpu_per_pod = min(self.cpu_per_pod * 2, self.MAX_CPU_PER_POD)
            self.memory_per_pod = min(self.memory_per_pod * 2, self.MAX_MEM_PER_POD)
        elif action == 4:
            # Decrease resources per pod
            # Can't have 0 resources though
            self.cpu_per_pod = max(100, self.cpu_per_pod / 2)
            self.memory_per_pod = max(64, self.memory_per_pod / 2)

        # Simulate traffic and environment dynamics
        self._simulate_environment()

        # Calculate reward
        reward = self._calculate_reward()

        # Check if terminated or truncated
        terminated = False  
        truncated = self.current_step >= self.max_steps

        info = {
            'num_pods': self.num_pods,
            'cpu_per_pod': self.cpu_per_pod,
            'memory_per_pod': self.memory_per_pod
        }

        return self.state, reward, terminated, truncated, info

    def get_value_at_timestep(self, t, total_timesteps, peak_value):
        # Normalize the timestep to the range [-1, 1]
        normalized_t = 2 * (t / total_timesteps) - 1
        # Apply the quadratic formula
        value = peak_value * (1 - normalized_t**2)
        return value

    def _simulate_environment(self):
        traffic = self.get_value_at_timestep(self.current_step, self.max_steps, 10000)
        self.state[2] = traffic 

        # Define CPU and memory consumption per request
        cpu_per_request = 0.2   # CPU units per request
        mem_per_request = 0.003 # Memory units per request

        # Define base CPU and memory consumption (overhead per pod)
        # These values are 10% of the default CPU and Memory (200 and 256)
        base_cpu_consumption = 0.76    # CPU 
        base_mem_consumption = 12.0    # Memory

        # Calculate pod resources 
        traffic_per_pod = traffic / self.num_pods
        cpu_needed_per_pod = traffic_per_pod * cpu_per_request
        mem_needed_per_pod = traffic_per_pod * mem_per_request

        # Calculate per-pod CPU and Memory usage percentages
        cpu_usage_per_pod = ((base_cpu_consumption + cpu_needed_per_pod) / self.cpu_per_pod) * 100
        cpu_usage_per_pod = cpu_usage_per_pod

        mem_usage_per_pod = ((base_mem_consumption + mem_needed_per_pod) / self.memory_per_pod) * 100
        mem_usage_per_pod = mem_usage_per_pod

        # Update the state
        self.state[0] = cpu_usage_per_pod
        self.state[1] = mem_usage_per_pod
        self.state[2] = traffic
        self.state[3] = 100 / self.num_pods  # Latency inversely proportional to the number of pods
        self.state[4] = self.num_pods
        self.state[5] = self.cpu_per_pod
        self.state[6] = self.memory_per_pod

    def _calculate_reward(self):
        cpu_usage = self.state[0]
        mem_usage = self.state[1]
        latency = self.state[3]

        reward = 100 * (1 - (abs(cpu_usage - 50) / 25))  # CPU reward
        reward += 100 * (1 - (abs(mem_usage - 50) / 50)) # Memory reward
        reward += 50 / latency                            # Latency reward
        reward -= 15 * self.num_pods                      # Basic # of pod punishment
        return reward

    def render(self, mode='human'):
        print(f"Step: {self.current_step}")
        print(f"Number of Pods: {self.num_pods}")
        print(f"Resources per Pod: CPU={self.cpu_per_pod} units, Memory={self.memory_per_pod} MB")
        print(f"State Metrics:")
        print(f"  CPU Usage: {self.state[0]:.2f}%")
        print(f"  Memory Usage: {self.state[1]:.2f}%")
        print(f"  Traffic per Second: {self.state[2]:.2f} req/s")
        print(f"  Latency: {self.state[3]:.2f} ms")
        print("-" * 40)

if __name__ == "__main__":
    # Create the environment
    env = NormalizeObservation(KubernetesEnv())
    print("Environment's Observation Space:", env.observation_space)

    # DQN agent
    model = DQN("MlpPolicy", env, verbose=1)

    # Train the agent
    model.learn(total_timesteps=100000)

    # Save the trained model
    model.save("dqn_kubernetes_env")

    # Test the trained agent
    obs, info = env.reset()
    terminated = False
    truncated = False
    total_reward = 0

    while not (terminated or truncated):
        env.render()
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

    print(f"Total Reward: {total_reward}")
    env.close()