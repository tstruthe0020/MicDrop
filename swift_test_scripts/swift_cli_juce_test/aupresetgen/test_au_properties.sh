#!/bin/bash
echo "🔬 Testing different Audio Unit properties with TDR Nova"

# Test what properties are actually available
.build/release/aupresetgen dump-params \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --verbose > au_properties.log 2>&1

echo "📄 Available properties saved to au_properties.log"
echo "File size: $(wc -l < au_properties.log) lines"

# Check if our test parameter values make sense
echo ""
echo "🔍 Analyzing our test parameters..."
echo "Parameter 50 (Band 1 Gain): We set 12.0, but AU expects 0.0-1.0 range"
echo "Parameter 52 (Band 1 Frequency): We set 40000.0, but AU expects 0.0-1.0 range"
echo ""
echo "💡 ISSUE: Our parameter values might be wrong!"
