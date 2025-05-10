import docker

def run_task_in_docker(image_name: str, environment_vars: dict):
    """
    Runs a task in a Docker container and returns its logs.

    Args:
        image_name: The name of the Docker image to run.
        environment_vars: A dictionary of environment variables to set in the container.

    Returns:
        The logs from the container as a string.
    """
    client = docker.from_env()
    container = None
    try:
        print(f"Running image {image_name} with env: {environment_vars}")
        container = client.containers.run(
            image_name,
            detach=True,
            environment=environment_vars,
            remove=False # Keep the container for log retrieval
        )
        result = container.wait()
        logs = container.logs().decode('utf-8').strip()
        print(f"Container {container.id} finished with status code: {result['StatusCode']}")
        return logs
    except docker.errors.ImageNotFound:
        print(f"Error: Image {image_name} not found.")
        return f"Error: Image {image_name} not found."
    except docker.errors.APIError as e:
        print(f"Docker API Error: {e}")
        return f"Docker API Error: {e}"
    finally:
        if container:
            try:
                container.remove(v=True) # Remove the container volume as well
                print(f"Container {container.id} removed.")
            except docker.errors.APIError as e:
                print(f"Error removing container {container.id}: {e}")

if __name__ == '__main__':
    # Example Usage (Requires the sub_agent_example image to be built first)
    # You would typically build the sub_agent_example first using:
    # cd src/sub_agent_example && docker build -t sub_agent_example:latest .
    print("Building sub_agent_example:latest image...")
    try:
        client = docker.from_env()
        # Build the image
        image, build_log = client.images.build(
            path="./src/sub_agent_example/", 
            tag="sub_agent_example:latest",
            rm=True # Remove intermediate containers
        )
        for line in build_log:
            if 'stream' in line:
                print(line['stream'].strip())
        print(f"Image {image.id} built successfully.")

        print("\nRunning example task...")
        env_vars = {"INPUT_TEXT": "Hello world from Docker orchestrator"}
        output_logs = run_task_in_docker("sub_agent_example:latest", env_vars)
        print("\nTask output:")
        print(output_logs)

        print("\nRunning example task with empty input...")
        env_vars_empty = {"INPUT_TEXT": ""}
        output_logs_empty = run_task_in_docker("sub_agent_example:latest", env_vars_empty)
        print("\nTask output (empty input):")
        print(output_logs_empty)

    except docker.errors.BuildError as e:
        print(f"Error building image: {e}")
        for line in e.build_log:
            if 'stream' in line:
                print(line['stream'].strip())
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 