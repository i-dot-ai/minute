#!/bin/bash

# Script to run Playwright E2E tests following the workflow in JUNIE_E2E_PROMPT.md
# Usage: ./scripts/run-tests.sh

# Navigate to the frontend folder
cd "$(dirname "$0")/../frontend" || { echo "Failed to navigate to frontend folder"; exit 1; }
echo "Changed directory to $(pwd)"

# Step 1: Initial Test Run & Discovery
echo "=== Step 1: Initial Test Run & Discovery ==="
echo "Running all tests to identify failing tests..."
npx playwright test --project=chromium --reporter=dot

# Create a directory for test results if it doesn't exist
mkdir -p ../test-results/reports
TEST_REPORT_FILE="../test-results/reports/test_report.md"
echo "# E2E Test Report" > "$TEST_REPORT_FILE"
echo "Generated on $(date)" >> "$TEST_REPORT_FILE"
echo "" >> "$TEST_REPORT_FILE"

# Find all test files
echo "Locating all Playwright test files..."
TEST_FILES=$(find ./tests -name "*.spec.ts")
echo "Found $(echo "$TEST_FILES" | wc -l | tr -d ' ') test files."

# Step 3: Individual Test Execution
echo "=== Step 3: Individual Test Execution ==="
echo "Running each test file individually..."

for test_file in $TEST_FILES; do
  echo "Running test: $test_file"
  echo "## Test: $test_file" >> "$TEST_REPORT_FILE"

  # Run the test and capture the output
  TEST_OUTPUT=$(npx playwright test "$test_file" --project=chromium --reporter=dot 2>&1)
  TEST_RESULT=$?

  # Record the result
  if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Test passed: $test_file"
    echo "Status: ✅ PASSED" >> "$TEST_REPORT_FILE"
  else
    echo "❌ Test failed: $test_file"
    echo "Status: ❌ FAILED" >> "$TEST_REPORT_FILE"
    echo "Error output:" >> "$TEST_REPORT_FILE"
    echo '```' >> "$TEST_REPORT_FILE"
    echo "$TEST_OUTPUT" >> "$TEST_REPORT_FILE"
    echo '```' >> "$TEST_REPORT_FILE"
  fi

  echo "" >> "$TEST_REPORT_FILE"
done

# Step 8: Collective Testing Verification
echo "=== Step 8: Collective Testing Verification ==="
echo "Running all tests together for final verification..."
FINAL_OUTPUT=$(npx playwright test --project=chromium --reporter=dot 2>&1)
FINAL_RESULT=$?

echo "## Final Verification" >> "$TEST_REPORT_FILE"
if [ $FINAL_RESULT -eq 0 ]; then
  echo "✅ All tests passed in final verification!"
  echo "Status: ✅ ALL TESTS PASSED" >> "$TEST_REPORT_FILE"
else
  echo "❌ Some tests failed in final verification."
  echo "Status: ❌ SOME TESTS FAILED" >> "$TEST_REPORT_FILE"
  echo "Error output:" >> "$TEST_REPORT_FILE"
  echo '```' >> "$TEST_REPORT_FILE"
  echo "$FINAL_OUTPUT" >> "$TEST_REPORT_FILE"
  echo '```' >> "$TEST_REPORT_FILE"
fi

echo "" >> "$TEST_REPORT_FILE"
echo "Test report saved to: $TEST_REPORT_FILE"
echo "All testing steps completed."
