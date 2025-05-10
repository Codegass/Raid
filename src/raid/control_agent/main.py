import sys
import os
import docker # Import docker to handle potential errors like BuildError

# Assuming an editable install, 'raid' package is importable.
from raid.docker_orchestrator.orchestrator import run_task_in_docker

# Calculate PROJECT_ROOT based on the new location of this file
# __file__ is .../src/raid/control_agent/main.py
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
RAID_PACKAGE_DIR = os.path.dirname(CURRENT_FILE_DIR)
SRC_DIR = os.path.dirname(RAID_PACKAGE_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)

SUB_AGENT_IMAGE_NAME = "sub_agent_example:latest"
# This path needs to point to src/sub_agent_example relative to project root
SUB_AGENT_DOCKERFILE_PATH = os.path.join(PROJECT_ROOT, "src", "sub_agent_example")

def build_sub_agent_image():
    """Builds the sub-agent Docker image."""
    print(f"Attempting to build Docker image {SUB_AGENT_IMAGE_NAME} from {SUB_AGENT_DOCKERFILE_PATH}...")
    try:
        client = docker.from_env()
        image, build_log = client.images.build(
            path=SUB_AGENT_DOCKERFILE_PATH,
            tag=SUB_AGENT_IMAGE_NAME,
            rm=True # Remove intermediate containers
        )
        print(f"Image {SUB_AGENT_IMAGE_NAME} built successfully (ID: {image.id}).")
        # for line in build_log:
        #     if 'stream' in line:
        #         print(line['stream'].strip())
        return True
    except docker.errors.BuildError as e:
        print(f"Error building image {SUB_AGENT_IMAGE_NAME}: {e}")
        # for line in e.build_log:
        #     if 'stream' in line:
        #         print(line['stream'].strip())
        return False
    except docker.errors.APIError as e:
        print(f"Docker API error during build: {e}")
        return False

def run_word_count_task(text_to_count: str):
    """
    Runs the word count task in the Sub-Agent.
    """
    print(f"Control Agent: Dispatching word count task for text: '{text_to_count}'")
    
    environment_vars = {"INPUT_TEXT": text_to_count}
    
    print(f"Control Agent: Invoking Docker Orchestrator to run image '{SUB_AGENT_IMAGE_NAME}'")
    task_output = run_task_in_docker(SUB_AGENT_IMAGE_NAME, environment_vars)
    
    print("\nControl Agent: Received output from Docker Orchestrator:")
    print("----------------------------------------------------")
    print(task_output)
    print("----------------------------------------------------")
    # In a real scenario, you would parse this output to get the actual result.
    # For v0.1, printing is sufficient.
    return task_output

if __name__ == "__main__":
    print("Control Agent v0.1 Initializing...")
    
    # 1. Ensure the Sub-Agent image is built
    # Check if image exists
    client = docker.from_env()
    try:
        client.images.get(SUB_AGENT_IMAGE_NAME)
        print(f"Image '{SUB_AGENT_IMAGE_NAME}' already exists. Skipping build.")
    except docker.errors.ImageNotFound:
        print(f"Image '{SUB_AGENT_IMAGE_NAME}' not found. Attempting to build...")
        if not build_sub_agent_image():
            print("Failed to build Sub-Agent image. Exiting.")
            sys.exit(1)
    except docker.errors.APIError as e:
        print(f"Docker API error checking for image: {e}. Exiting.")
        sys.exit(1)

    # 2. Define a hardcoded task
    task_input_text = "This is a test sentence for the Sub-Agent."
    
    # 3. Run the task
    run_word_count_task(task_input_text)
    
    print("\nControl Agent v0.1 Finished.") 