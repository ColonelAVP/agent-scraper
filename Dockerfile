# Use the official Python image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app
RUN echo "Set working directory to /app"

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN echo "Copied requirements.txt to the container"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN echo "Installed dependencies from requirements.txt"

# Download Spacy language model
RUN python -m spacy download en_core_web_sm
RUN echo "Downloaded Spacy language model"

# Copy the rest of the application files
COPY . .
RUN echo "Copied application files to the container"

# Expose the application port
EXPOSE 8000
RUN echo "Exposed port 8000"

# Run the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
