# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
# We use the requirements.txt file which excludes pyodbc for cloud compatibility
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable for port (Render sets this automatically)
ENV PORT=10000

# Run the application
# We use the $PORT environment variable provided by Render
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}"