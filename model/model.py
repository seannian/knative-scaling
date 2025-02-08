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
        self.MAX_MEM_PER_POD = 256   # Adjust as needed

        # Define observation space: 
        # [CPU Usage (%), Memory Usage (%), Concurrency, Latency (ms), Number of Pods, CPU per Pod, Memory per Pod]
        #
        # Here, concurrency ranges from 0 to 100 (instead of traffic up to 10,000).
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 1, 100, 128], dtype=np.float32),
            high=np.array([100, 100, 100, 1000, self.MAX_PODS, self.MAX_CPU_PER_POD, self.MAX_MEM_PER_POD], dtype=np.float32),
            dtype=np.float32
        )

        # Initial dynamic variables
        self.num_pods = 1
        self.cpu_per_pod = 250 
        self.memory_per_pod = 128  

        # Initial State:
        # CPU Usage = 1%
        # Memory Usage = 10%
        # Concurrency = 0
        # Latency = 100ms
        self.state = np.array([1, 10, 0, 100, self.num_pods, self.cpu_per_pod, self.memory_per_pod], dtype=np.float32) 
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
        self.cpu_per_pod = 250   
        self.memory_per_pod = 128  

        self.state = np.array([1, 10, 0, 100, self.num_pods, self.cpu_per_pod, self.memory_per_pod], dtype=np.float32)
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

        # Simulate environment
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
        """
        A helper function to simulate some time-based curve 
        (using a simple quadratic shape) that peaks at `peak_value` 
        and goes down to near 0 at the endpoints.
        """
        # Normalize the timestep to the range [-1, 1]
        normalized_t = 2 * (t / total_timesteps) - 1
        # Apply the quadratic formula
        value = peak_value * (1 - normalized_t**2)
        return value

    def _simulate_environment(self):
        concurrency = self.get_value_at_timestep(self.current_step, self.max_steps, 100)
        self.state[2] = concurrency 

        total_cpu = 1500 * (1 - math.exp(-0.05 * concurrency))
        total_mem = 21.5 * self.num_pods

        # Calculate per-pod concurrency
        concurrency_per_pod = concurrency / self.num_pods
        cpu_needed_per_pod = total_cpu / self.num_pods
        mem_needed_per_pod = total_mem / self.num_pods

        # Calculate per-pod CPU and Memory usage percentages
        cpu_usage_per_pod = ((cpu_needed_per_pod) / self.cpu_per_pod) * 100
        mem_usage_per_pod = ((mem_needed_per_pod) / self.memory_per_pod) * 100

        # Update the state
        self.state[0] = cpu_usage_per_pod
        self.state[1] = mem_usage_per_pod
        self.state[2] = concurrency
        self.state[3] = 0.24 * concurrency # ratio for latency
        self.state[4] = self.num_pods
        self.state[5] = self.cpu_per_pod
        self.state[6] = self.memory_per_pod

    def _calculate_reward(self):
        # Unpack relevant state variables
        cpu_usage   = self.state[0]
        mem_usage   = self.state[1]   # if you need it later
        concurrency = self.state[2]
        latency     = self.state[3]   # measured latency if desired

        # 1) CPU usage reward (Gaussian around 80%)
        target_cpu = 80.0
        sigma_cpu  = 10.0
        cpu_reward = np.exp(-((cpu_usage - target_cpu) / sigma_cpu) ** 2)

        # 2) Toy latency model parameters (tune to your environment)
        alpha = 10.0    # base latency cost
        beta  = 0.05    # how quickly latency grows with concurrency/pod
        gamma = 0.1     # overhead cost per pod

        # 3) Compute the toy-model latency
        #    concurrency_per_pod = concurrency / N
        #    toy_latency = alpha + beta*(C/N) + gamma*N
        concurrency_per_pod = concurrency / self.num_pods if self.num_pods > 0 else concurrency
        toy_latency = alpha + beta * concurrency_per_pod + gamma * self.num_pods

        # 4) Convert toy_latency to a reward:
        #    One simple approach: reward = 1 / (1 + toy_latency), so smaller = better
        #    Or you could do an exponential penalty: exp(-toy_latency / some_scale)
        toy_latency_reward = 1.0 / (1.0 + toy_latency)

        # 5) Combine CPU reward and latency reward (weights up to you)
        #    Example: weight both equally
        reward = 0.5 * cpu_reward + 0.5 * toy_latency_reward

        return reward

    def render(self, mode='human'):
        print(f"Step: {self.current_step}")
        print(f"Number of Pods: {self.num_pods}")
        print(f"Resources per Pod: CPU={self.cpu_per_pod} units, Memory={self.memory_per_pod} MB")
        print(f"State Metrics:")
        print(f"  CPU Usage: {self.state[0]:.2f}%")
        print(f"  Memory Usage: {self.state[1]:.2f}%")
        print(f"  Concurrency: {self.state[2]:.2f}")
        print(f"  Latency: {self.state[3]:.2f} ms")
        print("-" * 40)


if __name__ == "__main__":
    # Create the environment (wrapped to normalize observations)
    env = NormalizeObservation(KubernetesEnv())
    print("Environment's Observation Space:", env.observation_space)

    # DQN agent
    model = PPO("MlpPolicy", env, verbose=1)

    # Train the agent
    model.learn(total_timesteps=100000)

    # Save the trained model
    model.save("ppo_kubernetes_env")

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