import os
import sys
import subprocess

def main():
    # 1. Locate the docker-compose file inside the installed package
    package_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.join(package_dir, 'docker-compose.yml')
    
    # 2. Get the user's current folder (Target for analysis)
    user_cwd = os.getcwd()

    if not os.path.exists(compose_file):
        print(f"❌ Error: Cannot find {compose_file}")
        sys.exit(1)

    # 3. Pass the user's folder to Docker via environment variable
    # We copy the existing environment so we don't lose system paths
    env = os.environ.copy()
    env["TARGET_CODE_DIR"] = user_cwd

    # 4. Construct the Docker Command
    # We point to /app/src/cli.py because that is where we mounted the engine
    cmd = [
        "docker-compose", 
        "-f", compose_file, 
        "run", "--rm", 
        "indexer", 
        "python", "/app/src/cli.py" 
    ] + sys.argv[1:]  # Append any arguments the user typed (e.g., impact "login")

    # 5. Execute
    try:
        # We must pass 'env' here so docker-compose sees TARGET_CODE_DIR
        subprocess.run(cmd, env=env, check=False)
    except KeyboardInterrupt:
        print("\n👋 N3MO: Stopped by user.")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()