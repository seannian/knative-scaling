# -----------------------------------------------------------------------------
# Function: main
# Description:
#     The main entry point of the script. It initializes the Kubernetes environment,
#     loads a pre-trained DQN model, and makes a prediction based on a sample observation.
# 
# Parameters:
#     None
# 
# Returns:
#     None
# -----------------------------------------------------------------------------
import numpy as np
from stable_baselines3 import DQN
from kubernetes_env import KubernetesEnv

def main():
    env = KubernetesEnv()
    try:
        model = DQN.load("dqn_kubernetes_env.zip", env=env)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    sample_observation = np.array([50.0, 50.0, 5000.0, 100.0, 10, 400.0, 512.0], dtype=np.float32)
    sample_observation = sample_observation.reshape(1, -1)
    
    try:
        action, _ = model.predict(sample_observation, deterministic=True)
        print(f"Predicted Action: {int(action.item())}")
    except Exception as e:
        print(f"Error during prediction: {e}")

if __name__ == "__main__":
    main()