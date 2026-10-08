#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Accounting System Launcher${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Function to cleanup processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $API_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Start API server in background (suppress output so TUI terminal stays clean)
echo -e "${GREEN}Starting API server...${NC}"
python run_api.py > /dev/null 2>&1 &
API_PID=$!

# Wait for API to be ready
echo -e "${YELLOW}Waiting for API to start...${NC}"
for i in {1..30}; do
    if curl -s http://127.0.0.1:5001/auth/me > /dev/null 2>&1; then
        echo -e "${GREEN}API is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

# Start TUI
echo -e "${GREEN}Starting TUI client...${NC}"
python run_tui.py

# Cleanup when TUI exits
cleanup
