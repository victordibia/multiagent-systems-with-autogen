#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Print commands and their arguments as they are executed
set -x

# Run the generate_meta.py script
python course/generate_meta.py course/samples/

# Run the generate_results.py script
python course/generate_results.py course/samples/

echo "Generation scripts completed successfully!"