# Use the official Python image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Create and activate a virtual environment for better isolation
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download Spacy language model
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application files into the container
COPY . .

# Expose the application port
EXPOSE 8000

# Run the FastAPI app with Uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
