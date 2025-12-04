#!/bin/bash
# Server run script
cd server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

