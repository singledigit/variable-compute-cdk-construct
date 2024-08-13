# Use the official Python image from the Docker Hub
FROM python:3.12

RUN pwd

# Argument for function location
ARG FUNCTION_LOCATION

# Set the working directory
WORKDIR /app

# Copy the FastAPI application into the container
COPY variable_compute/wrapper/. .

# Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# # Copy Lambda folder to container
COPY $FUNCTION_LOCATION ./func

# # Install Lambda dependencies
RUN cd ./func && pip install --no-cache-dir -r requirements.txt

# Command to run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]