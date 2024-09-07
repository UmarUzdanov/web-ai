#!/bin/bash

# Name of the Bash script: run_allure_analyzer.sh

# Conda environment name
CONDA_ENV="open-ai"

# Python script name
PYTHON_SCRIPT="allure_test_analyzer.py"

# Project directory
PROJECT_DIR="/Users/umaruzdanov/PycharmProjects/open-webui"

# Check if conda is available
if ! command -v conda &> /dev/null
then
    echo "Conda is not available. Please install Conda and try again."
    exit 1
fi

# Activate the Conda environment
echo "Activating Conda environment: $CONDA_ENV"
eval "$(conda shell.bash hook)"
conda activate $CONDA_ENV

# Check if the environment was activated successfully
if [ $? -ne 0 ]; then
    echo "Failed to activate Conda environment: $CONDA_ENV"
    exit 1
fi

# Change to the project directory
cd "$PROJECT_DIR" || exit 1

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: $PYTHON_SCRIPT not found in the current directory."
    exit 1
fi

# Run the Python script
echo "Running Allure Test Analyzer..."
python "$PYTHON_SCRIPT"

# Check if the Python script executed successfully
if [ $? -eq 0 ]; then
    echo "Allure Test Analyzer completed successfully."
else
    echo "Error: Allure Test Analyzer encountered an issue."
    exit 1
fi

# Deactivate the Conda environment
conda deactivate