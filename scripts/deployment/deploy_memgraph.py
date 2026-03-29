#!/usr/bin/env python3
"""
Deploy Memgraph database for GMNAP V7 development
"""

import subprocess
import time
import sys
import os
from pathlib import Path


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker available: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker not responding")
            return False
    except FileNotFoundError:
        print("❌ Docker not installed")
        return False


def stop_existing_memgraph():
    """Stop any existing Memgraph containers."""
    print("🔍 Checking for existing Memgraph containers...")

    try:
        # Check for running containers
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--format",
                "{{.Names}}",
                "--filter",
                "name=gmnap-memgraph",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            print("🛑 Stopping existing Memgraph container...")
            subprocess.run(["docker", "stop", "gmnap-memgraph"], check=True)
            subprocess.run(["docker", "rm", "gmnap-memgraph"], check=True)
            print("✅ Existing container removed")
        else:
            print("✅ No existing containers found")

    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error checking existing containers: {e}")


def deploy_memgraph():
    """Deploy Memgraph using Docker."""
    print("🚀 Deploying Memgraph database...")

    # Create data directory for persistence
    data_dir = Path("./data/memgraph")
    data_dir.mkdir(parents=True, exist_ok=True)

    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        "gmnap-memgraph",
        "-p",
        "7687:7687",  # Bolt protocol port
        "-p",
        "7444:7444",  # HTTP monitoring port
        "-p",
        "3000:3000",  # Memgraph Lab port
        "-v",
        f"{data_dir.absolute()}:/var/lib/memgraph",  # Persist data
        "-e",
        "MEMGRAPH_USER=gmnap",
        "-e",
        "MEMGRAPH_PASSWORD=v7_lineage",
        "memgraph/memgraph:latest",
    ]

    try:
        print(f"📦 Running: {' '.join(docker_cmd)}")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        print(f"✅ Memgraph container started: {container_id[:12]}...")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Memgraph: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def wait_for_memgraph(timeout=60):
    """Wait for Memgraph to be ready."""
    print("⏳ Waiting for Memgraph to be ready...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to connect using docker exec
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "gmnap-memgraph",
                    "mgconsole",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "7687",
                    "--use-ssl=false",
                    "--username",
                    "gmnap",
                    "--password",
                    "v7_lineage",
                    "--non-interactive",
                    "--query",
                    "RETURN 1;",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ Memgraph is ready!")
                return True

        except Exception as e:
            pass

        print(".", end="", flush=True)
        time.sleep(2)

    print(f"\n❌ Memgraph not ready after {timeout}s")
    return False


def test_memgraph_connection():
    """Test Memgraph connection with Python client."""
    print("🧪 Testing Memgraph connection with Python client...")

    # Add src to path for testing
    sys.path.insert(0, str(Path(__file__).parent / "src"))

    try:
        from core.memgraph_client import MemgraphClient

        # Create client with real connection (not mock)
        client = MemgraphClient(use_mock=False)

        if client.is_connected():
            print("✅ Python client connected successfully")

            # Test basic operations
            test_entry = {
                "GlobalID": "deploy-test-001",
                "CanonicalLatin": "Test Mathematician",
                "BirthYear": 1950,
                "DetectedRegion": "A1",
                "DetectionConfidence": 0.95,
            }

            success = client.create_mathematician(test_entry)
            if success:
                print("✅ Test mathematician creation successful")
            else:
                print("❌ Test mathematician creation failed")

            # Get metrics
            metrics = client.get_graph_metrics()
            print(
                f"✅ Graph metrics retrieved: {metrics.total_mathematicians} mathematicians"
            )

            client.close()
            return True
        else:
            print("❌ Python client connection failed")
            return False

    except Exception as e:
        print(f"❌ Python client test failed: {e}")
        return False


def show_connection_info():
    """Show connection information."""
    print("\n" + "=" * 60)
    print("🎯 MEMGRAPH CONNECTION INFO")
    print("=" * 60)
    print("Database URL: bolt://localhost:7687")
    print("Username: gmnap")
    print("Password: v7_lineage")
    print("Memgraph Lab: http://localhost:3000")
    print("Monitoring: http://localhost:7444")
    print()
    print("Container management:")
    print("  docker logs gmnap-memgraph        # View logs")
    print("  docker stop gmnap-memgraph        # Stop database")
    print("  docker start gmnap-memgraph       # Start database")
    print(
        "  docker exec -it gmnap-memgraph mgconsole --host 127.0.0.1 --port 7687 --use-ssl=false"
    )
    print("=" * 60)


def main():
    """Deploy Memgraph for GMNAP V7 development."""
    print("🔥 GMNAP V7 - MEMGRAPH DATABASE DEPLOYMENT")
    print("=" * 60)

    # Check prerequisites
    if not check_docker():
        print("❌ Docker is required to deploy Memgraph")
        return False

    # Stop existing containers
    stop_existing_memgraph()

    # Deploy new container
    if not deploy_memgraph():
        return False

    # Wait for startup
    if not wait_for_memgraph():
        print("❌ Memgraph deployment failed - container not responding")
        return False

    # Test connection
    if not test_memgraph_connection():
        print("⚠️ Memgraph deployed but Python client connection failed")
        print(
            "   This might be normal - the container may need more time to initialize"
        )

    # Show connection info
    show_connection_info()

    print("\n🚀 MEMGRAPH DEPLOYMENT COMPLETE")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
