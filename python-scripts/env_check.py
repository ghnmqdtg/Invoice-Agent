#!/usr/bin/env python3
"""
Test script to verify the invoice-agent virtual environment and requests package
"""

import sys
import os
import requests
from datetime import datetime


def Check_virtual_env():
    """Check that we're running in the correct virtual environment"""
    print("=== Virtual Environment Check ===")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Virtual env: {os.environ.get('VIRTUAL_ENV', 'Not in virtual env')}")
    print()


def Check_requests():
    """Check that requests package works"""
    print("=== Requests Package Check ===")
    try:
        response = requests.get("https://httpbin.org/json")
        if response.status_code == 200:
            print("Requests package working correctly!")
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
        else:
            print(f"Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"Error testing requests: {e}")
    print()


def Check_shared_volume():
    """Check that shared volume is accessible"""
    print("=== Shared Volume Check ===")
    try:
        test_file = "shared/test_from_python.txt"
        with open(test_file, "w") as f:
            f.write(f"Test from Python container at {datetime.now()}")
        print(f"Successfully wrote to shared volume: {test_file}")

        # Read it back
        with open(test_file, "r") as f:
            content = f.read()
        print(f"Successfully read from shared volume: {content}")
    except Exception as e:
        print(f"Error testing shared volume: {e}")
    print()


if __name__ == "__main__":
    print("Invoice Agent Python Environment Test")
    print("=" * 50)

    Check_virtual_env()
    Check_requests()
    Check_shared_volume()

    print("All tests completed!")
