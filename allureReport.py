import requests
from requests.auth import HTTPBasicAuth
import json
import os
from datetime import datetime


class AllureTestCaseFetcher:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)

    def fetch_test_case(self, test_case_id):
        url = f"{self.base_url}/test-cases/{test_case_id}.json"
        response = requests.get(url, auth=self.auth)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return None

    def get_before_stages_steps(self, test_case_data):
        before_stages = test_case_data.get("beforeStages", [])
        all_steps = []

        for stage in before_stages:
            steps = stage.get("steps", [])
            for step in steps:
                all_steps.append(step["name"])

        return all_steps


# Jenkins credentials
username = "uzdanovQA"
password = "W/f?4x:#Z=5#$NN^"

# Base URL for Allure data
base_url = "http://52.1.51.128:8080/job/NZDPU%20DEV/allure/data"

# URL for the Allure categories data
categories_url = f"{base_url}/categories.json"

# Output directory
output_dir = "/Users/umaruzdanov/Documents/Failed tests Allure Report"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Generate a filename with the current date and time
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"failed_tests_{current_time}.txt")

# Send GET request
response = requests.get(categories_url, auth=HTTPBasicAuth(username, password))


# Function to write output to both console and file
def write_output(file, message):
    print(message)
    file.write(message + "\n")


# Check if the request was successful
if response.status_code == 200:
    # Parse JSON data
    data = json.loads(response.text)

    with open(output_file, "w") as f:
        write_output(f, "Failed Tests and Reasons:")

        fetcher = AllureTestCaseFetcher(base_url, username, password)

        # Function to recursively search for failed tests
        def find_failed_tests(node):
            if isinstance(node, dict):
                if node.get("status") == "failed":
                    test_name = node.get("name", "Unknown Test")
                    test_uid = node.get("uid", "Unknown UID")
                    parent_uid = node.get("parentUid", "Unknown Parent UID")
                    failure_reason = find_failure_reason(data, parent_uid)
                    write_output(f, f"Failed Test: {test_name}")
                    write_output(f, f"Test UID: {test_uid}")
                    write_output(f, f"Parent UID: {parent_uid}")
                    write_output(f, f"Failure Reason: {failure_reason}")

                    # Fetch and print beforeStages steps
                    test_case_data = fetcher.fetch_test_case(test_uid)
                    if test_case_data:
                        steps = fetcher.get_before_stages_steps(test_case_data)
                        write_output(f, f"Steps from beforeStages:")
                        for i, step in enumerate(steps, 1):
                            write_output(f, f"{i}. {step}")
                    else:
                        write_output(f, "Failed to fetch test case data.")

                    write_output(f, "---")
                for value in node.values():
                    find_failed_tests(value)
            elif isinstance(node, list):
                for item in node:
                    find_failed_tests(item)

        # Function to find the failure reason
        def find_failure_reason(node, parent_uid):
            if isinstance(node, dict):
                if node.get("uid") == parent_uid:
                    return node.get("name", "Unknown Reason")
                for value in node.values():
                    reason = find_failure_reason(value, parent_uid)
                    if reason:
                        return reason
            elif isinstance(node, list):
                for item in node:
                    reason = find_failure_reason(item, parent_uid)
                    if reason:
                        return reason
            return None

        find_failed_tests(data)

    print(f"Output has been saved to: {output_file}")
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
