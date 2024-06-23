# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files into the container
COPY app/ ./app
COPY tests/ ./tests

# Set the environment variable for Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Set the entrypoint to run the Python script
ENTRYPOINT ["python", "-m", "app.load_tester"]

# Set default command line arguments
CMD ["http://example.com", "--qps", "10", "--duration", "5"]