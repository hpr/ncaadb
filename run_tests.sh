#!/bin/bash
set -e

cd "$(dirname "$0")"

failed=0

for test in tests/test_*.py; do
    echo "=== Running $test ==="
    if python3 "$test"; then
        echo ""
    else
        echo "FAILED: $test"
        failed=1
    fi
done

if [ $failed -ne 0 ]; then
    echo "Some tests failed."
    exit 1
fi

echo "All tests passed."
