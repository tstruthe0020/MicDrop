#!/bin/bash

# Swift CLI Test Script for Vocal Chain Assistant
# This script tests the new Swift CLI tool with your plugin seeds

set -e  # Exit on any error

# Configuration
SWIFT_CLI="./aupresetgen/.build/release/aupresetgen"
SEED_DIR="/Users/theostruthers/Desktop/Plugin Seeds"
TEST_OUTPUT_DIR="/tmp/swift_cli_test"
VALUES_DIR="/app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎵 Swift CLI Test Suite for Vocal Chain Assistant${NC}"
echo "=================================================="

# Create test output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Function to test a plugin
test_plugin() {
    local plugin_name="$1"
    local seed_file="$2"
    local values_file="$3"
    local map_file="$4"
    
    echo -e "\n${YELLOW}Testing $plugin_name...${NC}"
    
    if [ ! -f "$seed_file" ]; then
        echo -e "${RED}❌ Seed file not found: $seed_file${NC}"
        return 1
    fi
    
    if [ ! -f "$values_file" ]; then
        echo -e "${RED}❌ Values file not found: $values_file${NC}"
        return 1
    fi
    
    # Test 1: Discover plugin info
    echo "  🔍 Discovering plugin info..."
    if $SWIFT_CLI --seed "$seed_file" --values "$values_file" --preset-name "test" --out-dir "$TEST_OUTPUT_DIR" --discover --verbose; then
        echo -e "  ${GREEN}✅ Plugin discovery successful${NC}"
    else
        echo -e "  ${RED}❌ Plugin discovery failed${NC}"
        return 1
    fi
    
    # Test 2: List parameters
    echo "  📋 Listing parameters..."
    if $SWIFT_CLI --seed "$seed_file" --values "$values_file" --preset-name "test" --out-dir "$TEST_OUTPUT_DIR" --list-params; then
        echo -e "  ${GREEN}✅ Parameter listing successful${NC}"
    else
        echo -e "  ${RED}❌ Parameter listing failed${NC}"
        return 1
    fi
    
    # Test 3: Dry run (check parameter mapping)
    echo "  🧪 Testing parameter mapping (dry run)..."
    local map_arg=""
    if [ -f "$map_file" ]; then
        map_arg="--map $map_file"
    fi
    
    if $SWIFT_CLI --seed "$seed_file" --values "$values_file" --preset-name "Test_${plugin_name}" --out-dir "$TEST_OUTPUT_DIR" $map_arg --dry-run --verbose; then
        echo -e "  ${GREEN}✅ Parameter mapping successful${NC}"
    else
        echo -e "  ${RED}❌ Parameter mapping failed${NC}"
        return 1
    fi
    
    # Test 4: Generate actual preset
    echo "  🎛️  Generating preset..."
    if $SWIFT_CLI --seed "$seed_file" --values "$values_file" --preset-name "Test_${plugin_name}" --out-dir "$TEST_OUTPUT_DIR" $map_arg --verbose --lint; then
        echo -e "  ${GREEN}✅ Preset generation successful${NC}"
        
        # Find the generated file
        local generated_file=$(find "$TEST_OUTPUT_DIR" -name "Test_${plugin_name}.aupreset" -type f | head -1)
        if [ -f "$generated_file" ]; then
            local file_size=$(stat -f%z "$generated_file" 2>/dev/null || stat -c%s "$generated_file" 2>/dev/null || echo "unknown")
            echo -e "  ${GREEN}📁 Generated: $generated_file (${file_size} bytes)${NC}"
            
            # Quick validation
            if plutil -lint "$generated_file" >/dev/null 2>&1; then
                echo -e "  ${GREEN}✅ File format validation passed${NC}"
            else
                echo -e "  ${RED}❌ File format validation failed${NC}"
                return 1
            fi
        else
            echo -e "  ${RED}❌ Generated file not found${NC}"
            return 1
        fi
    else
        echo -e "  ${RED}❌ Preset generation failed${NC}"
        return 1
    fi
    
    echo -e "  ${GREEN}🎉 $plugin_name test completed successfully!${NC}"
    return 0
}

# Main test execution
echo -e "\n${BLUE}Starting plugin tests...${NC}"

# Test TDR Nova (XML format)
echo -e "\n${BLUE}=== Testing TDR Nova (XML format) ===${NC}"
test_plugin "TDRNova" \
    "$SEED_DIR/TDR Nova.aupreset" \
    "$VALUES_DIR/swift_test_values_tdrnova.json" \
    "/app/aupreset/maps/TDRNova.map.json"

# Test MEqualizer (Binary format)
echo -e "\n${BLUE}=== Testing MEqualizer (Binary format) ===${NC}"
test_plugin "MEqualizer" \
    "$SEED_DIR/MEqualizer.aupreset" \
    "$VALUES_DIR/swift_test_values_mequalizer.json" \
    "/app/aupreset/maps/MEqualizer.map.json"

# Summary
echo -e "\n${BLUE}=== Test Results Summary ===${NC}"
echo "Test output directory: $TEST_OUTPUT_DIR"
echo "Generated presets:"
find "$TEST_OUTPUT_DIR" -name "*.aupreset" -type f -exec ls -la {} \;

echo -e "\n${GREEN}🎊 All tests completed!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the generated presets in Logic Pro"
echo "2. Verify parameter changes are applied correctly"
echo "3. If successful, integrate with backend system"

echo -e "\n${BLUE}Generated files location:${NC} $TEST_OUTPUT_DIR"
echo -e "${BLUE}To test in Logic Pro:${NC}"
echo "1. Copy .aupreset files to ~/Library/Audio/Presets/"
echo "2. Or drag-drop directly onto plugins in Logic Pro"