#!/bin/bash

# Colors for better readability
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
CYAN="\033[0;36m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Constants
TEST_ENV_DIR="/tmp/testing"
MCPO_SERVER_DIR="$TEST_ENV_DIR/mcpo_simple_server"

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src/mcpo_simple_server"

# Function to prepare the isolated test environment
prepare_test_env() {
    local clean_env=$1
    
    # Create test environment directory if it doesn't exist
    if [[ ! -d "$TEST_ENV_DIR" ]]; then
        mkdir -p "$TEST_ENV_DIR"
        clean_env="y" # Force clean if directory didn't exist
    fi
    
    # If clean environment requested, remove and recreate
    if [[ "$clean_env" == "y" ]]; then
        echo -e "${BLUE}Creating fresh test environment...${NC}"
        
        # Remove existing directory if it exists
        echo -e "${BLUE}Removing existing test environment at $MCPO_SERVER_DIR...${NC}"
        if [[ -d "$MCPO_SERVER_DIR" ]]; then
            rm -rf "$MCPO_SERVER_DIR"
        fi
        
        # Copy source files to test environment
        echo -e "${BLUE}Creating test environment at $MCPO_SERVER_DIR...${NC}"
        mkdir -p "$MCPO_SERVER_DIR"
        cp -r "$SRC_DIR"/* "$MCPO_SERVER_DIR"/

        # Create empty data directory
        mkdir -p "$MCPO_SERVER_DIR/data"
        
        echo -e "${GREEN}Test environment prepared at $MCPO_SERVER_DIR${NC}"
    else
        echo -e "${BLUE}Using existing test environment at $MCPO_SERVER_DIR${NC}"
        
        # Ensure the directory exists even if we're not cleaning
        if [[ ! -d "$MCPO_SERVER_DIR" ]]; then
            echo -e "${YELLOW}Warning: Test environment doesn't exist. Creating it now...${NC}"
            mkdir -p "$MCPO_SERVER_DIR"
            cp -r "$SRC_DIR"/* "$MCPO_SERVER_DIR"/
            mkdir -p "$MCPO_SERVER_DIR/data"
        fi
    fi
}

# Find all test files and sort them
cd "$SCRIPT_DIR"
TEST_FILES=($(find . -name "test_*.py" | sort))

# Create an associative array to map test IDs to filenames
declare -A TEST_ID_MAP

# Build the mapping of test IDs to filenames
for TEST_FILE in "${TEST_FILES[@]}"; do
    # Extract the test name without path and extension
    TEST_NAME=$(basename "$TEST_FILE" .py)
    
    # Extract the ID from the test name (e.g., "test_001_health" -> "001")
    TEST_ID=$(echo "$TEST_NAME" | sed -n 's/test_\([0-9]\+\)_.*/\1/p')
    
    # Store the mapping of ID to filename
    TEST_ID_MAP["$TEST_ID"]="$TEST_NAME"
done

# Function to run a test with the given ID
run_test() {
    local test_id=$1
    local clean_env=$2
    
    # Handle 'a' or 'all' to run all tests
    if [[ "$test_id" == "a" || "$test_id" == "all" ]]; then
        echo -e "${YELLOW}Running all tests...${NC}"
        prepare_test_env "$clean_env"
        
        # Set PYTHONPATH to include the test environment
        export PYTHONPATH="$TEST_ENV_DIR:$PYTHONPATH"
        
        cd "$PROJECT_ROOT"
        if [[ "$clean_env" == "y" ]]; then
            python -m pytest "$SCRIPT_DIR" -v --clean
        else
            python -m pytest "$SCRIPT_DIR" -v
        fi
        return $?
    fi
    
    # Check if the ID exists in our map
    if [[ -z "${TEST_ID_MAP[$test_id]}" ]]; then
        echo -e "${RED}Invalid test ID: $test_id${NC}"
        echo -e "${YELLOW}Available test IDs:${NC} $(echo "${!TEST_ID_MAP[@]}" | tr ' ' ',' | sed 's/,/, /g')"
        return 1
    fi
    
    # Get the test name from the ID
    local test_name="${TEST_ID_MAP[$test_id]}"
    
    echo -e "${YELLOW}Running test: ${CYAN}$test_name${NC}"
    prepare_test_env "$clean_env"
    
    # Set PYTHONPATH to include the test environment
    export PYTHONPATH="$TEST_ENV_DIR:$PYTHONPATH"
    
    cd "$PROJECT_ROOT"
    if [[ "$clean_env" == "y" ]]; then
        python -m pytest "$SCRIPT_DIR/$test_name.py" -v --clean
    else
        python -m pytest "$SCRIPT_DIR/$test_name.py" -v
    fi
    return $?
}

# Check if a test ID was provided as a command-line argument
if [[ $# -ge 1 ]]; then
    TEST_ID="$1"
    CLEAN_ENV="n"  # Default to using existing environment
    
    # Check if a second argument was provided for clean option
    if [[ $# -ge 2 ]]; then
        if [[ "$2" == "--clean" ]]; then
            CLEAN_ENV="y"
        fi
    fi
    
    run_test "$TEST_ID" "$CLEAN_ENV"
    exit $?
fi

# If no argument was provided, show the interactive menu
# Display the list of tests with their IDs
echo -e "${YELLOW}Available tests:${NC}"
for TEST_ID in $(echo "${!TEST_ID_MAP[@]}" | tr ' ' '\n' | sort -n); do
    TEST_NAME="${TEST_ID_MAP[$TEST_ID]}"
    echo -e "${GREEN}[$TEST_ID]${NC} ${CYAN}$TEST_NAME${NC}"
done

# Ask the user to select a test
echo -e "\n${YELLOW}Enter the ID of the test you want to run (or 'a' for all tests):${NC}"
read -r TEST_ID

# Ask if the user wants a clean environment
echo -e "\n${YELLOW}Run with clean environment? This will copy fresh code to $MCPO_SERVER_DIR [y/n]:${NC}"
read -r CLEAN_ENV

# Validate input
if [[ "$CLEAN_ENV" != "y" && "$CLEAN_ENV" != "n" ]]; then
    CLEAN_ENV="y"  # Default to yes if invalid input
    echo -e "${BLUE}Invalid option. Defaulting to clean environment.${NC}"
fi

# Run the selected test
run_test "$TEST_ID" "$CLEAN_ENV"
