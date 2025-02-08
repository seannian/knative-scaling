import os
import subprocess
import time

# -----------------------------------------------------------------------------
# Function: main
# Description:
#     Main function to run experiments with different concurrency levels.
#     It iterates through predefined concurrency levels, sets environment
#     variables, executes the pipeline script, and pauses between runs.
#
# Parameters:
#     None
#
# Returns:
#     None
# -----------------------------------------------------------------------------
def main():
    concurrency_levels = [5, 10, 20, 30, 40, 50, 75, 100]
    request_duration = "120"
    repetitions = 1

    for c in concurrency_levels:
        for i in range(repetitions):
            os.environ["REQUEST_DURATION"] = request_duration
            os.environ["CONCURRENCY"] = str(c)

            print(f"\n[INFO] Running pipeline with CONCURRENCY={c}, REQUEST_DURATION={request_duration}s (Iteration {i + 1}/{repetitions})")

            try:
                subprocess.run(["python3", "pipeline.py"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] pipeline.py failed with error: {e}")
                continue

            time.sleep(5)

if __name__ == "__main__":
    main()