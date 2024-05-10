#!/bin/bash
find ../subjects/ -type f -name "table*.csv" -exec sh -c 'echo "=== {} ==="; cat {}' \;