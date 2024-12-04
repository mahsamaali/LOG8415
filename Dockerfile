FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y python3-pip && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY proxy.py /code/
# Copy application code and configuration
COPY config.json /code/config.json 
WORKDIR /code

# Expose port
EXPOSE 8000

# Run the Flask app
CMD ["python", "proxy.py"]
