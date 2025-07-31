# Use a lightweight base image
FROM alpine:latest

# Set the working directory
WORKDIR /app

# A command to run when the container starts
CMD ["echo", "Hello from Docker!"]