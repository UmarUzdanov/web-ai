import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
import re
from collections import defaultdict
import os
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Configuration
BASE_URL = "http://52.1.51.128:8080/job/NZDPU%20DEV/allure/data"
USERNAME = "uzdanovQA"
PASSWORD = "W/f?4x:#Z=5#$NN^"
OUTPUT_DIR = os.path.expanduser("~/Documents/Failed tests Allure Report")

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Data class to store information about a test case."""

    name: str
    uid: str
    parent_uid: str
    failure_reason: str


def categorize_failure(failure_reason: str) -> str:
    """Categorize the failure reason into predefined categories."""
    categories = [
        ("Element not found", "Element Not Found"),
        ("Timeout", "Timeout"),
        ("AssertionError", "Assertion Error"),
    ]
    for keyword, category in categories:
        if keyword in failure_reason:
            return category
    return "Other"


def generate_recommendations(
    failure_categories: Dict, setup_issues: Dict, total_tests: int
) -> str:
    """Generate recommendations based on test failures."""
    recommendations = ""
    if "Element Not Found" in failure_categories:
        recommendations += "- Review page layouts and element identifiers, especially on frequently accessed pages.\n"

    common_setup_steps = [
        step for step, count in setup_issues.items() if count > total_tests / 2
    ]
    for step in common_setup_steps:
        recommendations += (
            f"- Investigate the '{step}' step as it's involved in many test failures.\n"
        )

    if "Timeout" in failure_categories:
        recommendations += (
            "- Review and potentially increase timeout settings for slow operations.\n"
        )
    if "Assertion Error" in failure_categories:
        recommendations += (
            "- Review test assertions and expected outcomes for accuracy.\n"
        )

    return recommendations


def generate_summary(
    failure_categories: Dict,
    feature_failures: Dict,
    setup_issues: Dict,
    total_tests: int,
) -> str:
    """Generate a summary of test failures."""
    summary = "Test Failure Summary:\n\n"

    summary += "Failure Categories:\n"
    for category, tests in failure_categories.items():
        summary += f"{category}: {len(tests)} tests\n"
        for test, reason in tests[:3]:
            summary += f"  - {test}\n    Reason: {reason[:100]}...\n"
        if len(tests) > 3:
            summary += f"  ... and {len(tests) - 3} more\n"
        summary += "\n"

    summary += "Affected Features:\n"
    for feature, count in feature_failures.items():
        summary += f"{feature}: {count} failures\n"
    summary += "\n"

    summary += "Common Setup Steps in Failed Tests:\n"
    for step, count in sorted(setup_issues.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]:
        summary += f"{step}: appeared in {count} failed tests\n"
    summary += "\n"

    summary += "Recommendations:\n"
    summary += generate_recommendations(failure_categories, setup_issues, total_tests)

    return summary


def analyze_test_failures(file_path: str) -> str:
    """Analyze test failures and generate a summary."""
    with open(file_path, "r") as f:
        content = f.read()

    tests = content.split("---")
    failure_categories = defaultdict(list)
    setup_issues = defaultdict(int)
    feature_failures = defaultdict(int)

    feature_keywords = ["Admin", "Emissions", "User", "Report", "Dashboard"]

    for test in tests:
        if "Failed Test:" not in test:
            continue

        test_name = re.search(r"Failed Test: (.+)", test)
        failure_reason = re.search(r"Failure Reason: (.+)", test)

        if test_name and failure_reason:
            test_name = test_name.group(1)
            failure_reason = failure_reason.group(1)

            category = categorize_failure(failure_reason)
            failure_categories[category].append((test_name, failure_reason))

            for keyword in feature_keywords:
                if keyword.lower() in test_name.lower():
                    feature_failures[keyword] += 1
                    break

            setup_steps = re.findall(r"\d+\. (.+)", test)
            for step in setup_steps:
                setup_issues[step] += 1

    return generate_summary(
        failure_categories, feature_failures, setup_issues, len(tests)
    )


def get_before_stages_steps(test_case_data: Dict) -> List[str]:
    """Extract steps from before stages of a test case."""
    before_stages = test_case_data.get("beforeStages", [])
    return [step["name"] for stage in before_stages for step in stage.get("steps", [])]


class AllureTestAnalyzer:
    """Class to analyze test failures from Allure reports."""

    def __init__(self, base_url: str, username: str, password: str, output_dir: str):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.output_dir = output_dir
        self.categories_url = f"{self.base_url}/categories.json"
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_test_case(self, test_case_id: str) -> Optional[Dict]:
        """Fetch test case data from the API."""
        url = f"{self.base_url}/test-cases/{test_case_id}.json"
        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data for test case {test_case_id}: {e}")
            return None

    def find_failure_reason(self, node: Dict, parent_uid: str) -> Optional[str]:
        """Recursively find the failure reason in the test data."""
        if isinstance(node, dict):
            if node.get("uid") == parent_uid:
                return node.get("name", "Unknown Reason")
            for value in node.values():
                reason = self.find_failure_reason(value, parent_uid)
                if reason:
                    return reason
        elif isinstance(node, list):
            for item in node:
                reason = self.find_failure_reason(item, parent_uid)
                if reason:
                    return reason
        return None

    def find_failed_tests(self, node: Dict, data: Dict) -> List[TestCase]:
        """Recursively find failed tests in the data."""
        failed_tests = []
        if isinstance(node, dict):
            if node.get("status") == "failed":
                test_case = self.process_failed_test(node, data)
                if test_case:
                    failed_tests.append(test_case)
            for value in node.values():
                failed_tests.extend(self.find_failed_tests(value, data))
        elif isinstance(node, list):
            for item in node:
                failed_tests.extend(self.find_failed_tests(item, data))
        return failed_tests

    def process_failed_test(self, node: Dict, data: Dict) -> Optional[TestCase]:
        """Process a failed test and return a TestCase object."""
        test_name = node.get("name", "Unknown Test")
        test_uid = node.get("uid", "Unknown UID")
        parent_uid = node.get("parentUid", "Unknown Parent UID")
        failure_reason = self.find_failure_reason(data, parent_uid)
        if failure_reason:
            return TestCase(test_name, test_uid, parent_uid, failure_reason)
        return None

    def fetch_and_analyze(self) -> Optional[str]:
        """Fetch data from the API and analyze failed tests."""
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"failed_tests_{current_time}.txt")

        try:
            response = requests.get(self.categories_url, auth=self.auth)
            response.raise_for_status()
            data = response.json()

            failed_tests = self.find_failed_tests(data, data)

            with open(output_file, "w") as f:
                f.write("Failed Tests and Reasons:\n")
                for test in failed_tests:
                    f.write(f"Failed Test: {test.name}\n")
                    f.write(f"Test UID: {test.uid}\n")
                    f.write(f"Parent UID: {test.parent_uid}\n")
                    f.write(f"Failure Reason: {test.failure_reason}\n")

                    test_case_data = self.fetch_test_case(test.uid)
                    if test_case_data:
                        steps = get_before_stages_steps(test_case_data)
                        f.write("Steps from beforeStages:\n")
                        for i, step in enumerate(steps, 1):
                            f.write(f"{i}. {step}\n")
                    else:
                        f.write("Failed to fetch test case data.\n")
                    f.write("---\n")

            logger.info(f"Output has been saved to: {output_file}")
            return output_file
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from categories URL: {e}")
            return None

    def run_analysis(self) -> Optional[str]:
        """Run the complete analysis process."""
        output_file = self.fetch_and_analyze()
        if output_file:
            summary = analyze_test_failures(output_file)
            logger.info(summary)

            # Append the summary to the output file
            with open(output_file, "a") as f:
                f.write("\n\n" + "=" * 50 + "\n")
                f.write("ANALYSIS SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                f.write(summary)

            logger.info(f"Analysis summary appended to: {output_file}")
            return summary
        return None


if __name__ == "__main__":
    analyzer = AllureTestAnalyzer(BASE_URL, USERNAME, PASSWORD, OUTPUT_DIR)
    analyzer.run_analysis()
