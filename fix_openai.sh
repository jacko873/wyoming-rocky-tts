#!/bin/bash

# Fix OpenAI library version issue
echo "=========================================="
echo "Fixing OpenAI Library Version Issue"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Run this script from the wyoming-rocky-tts directory${NC}"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Current OpenAI version:${NC}"
venv/bin/pip show openai | grep Version || echo "Not installed"

echo ""
echo -e "${YELLOW}Uninstalling current OpenAI library...${NC}"
venv/bin/pip uninstall -y openai

echo ""
echo -e "${GREEN}Installing OpenAI 1.3.0 (stable version)...${NC}"
venv/bin/pip install openai==1.3.0

echo ""
echo -e "${GREEN}Verifying installation...${NC}"
venv/bin/pip show openai | grep Version

echo ""
echo -e "${GREEN}Testing OpenAI import...${NC}"
venv/bin/python -c "import openai; print(f'✅ OpenAI {openai.__version__} imported successfully')"

echo ""
echo -e "${GREEN}Restarting services...${NC}"
sudo systemctl restart wyoming-rocky
sudo systemctl restart wyoming-rocky-web

echo ""
echo -e "${GREEN}✅ OpenAI fix complete!${NC}"
echo ""
echo "You can now test OpenAI mode:"
echo "  1. Open web UI: http://your-server:8088"
echo "  2. Select 'OpenAI' from the style mode dropdown"
echo "  3. Test with: 'The lights are on'"
echo ""
echo "Or run: python3 test_openai_simple.py"