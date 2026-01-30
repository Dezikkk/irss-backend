#!/bin/sh

# Create the virtual environment
if [ ! -d ".venv" ]; then
	echo Virtual environment not found. Creating new...
	python -m venv .venv 
fi

# Install dependencies
if [ -f "requirements.txt" ]; then
	echo Installing dependencies.
	.venv/bin/pip install -r requirements.txt
else
	echo "File requirements.txt not found."
fi

# Run the thingy
.venv/bin/uvicorn app.main:app --reload
