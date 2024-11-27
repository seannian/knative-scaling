import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from stable_baselines3 import DQN
from gymnasium.wrappers import NormalizeObservation
import uvicorn
from kubernetes_env import KubernetesEnv

app = FastAPI()
env = KubernetesEnv()
model = DQN.load("model.zip", env=env)

class Observation(BaseModel):
    cpu_usage: float
    memory_usage: float
    traffic_per_second: float
    latency: float
    num_pods: int
    cpu_per_pod: float
    memory_per_pod: float

@app.post("/predict")
def predict(observation: Observation):
    obs = np.array([
        observation.cpu_usage,
        observation.memory_usage,
        observation.traffic_per_second,
        observation.latency,
        observation.num_pods,
        observation.cpu_per_pod,
        observation.memory_per_pod
    ], dtype=np.float32)

    action, _ = model.predict(obs, deterministic=True)
    return {"action": int(action)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
