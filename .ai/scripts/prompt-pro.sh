#!/bin/bash

# Check if a prompt was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <prompt>"
  exit 1
fi

# Combine all arguments as the prompt
PROMPT="$*"

# Run gemini with model pro and the provided prompt
gemini -m pro -p "$PROMPT"
