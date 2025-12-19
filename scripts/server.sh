#!/bin/bash
# Start the FastAPI server
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --port 8000

