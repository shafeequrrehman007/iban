# Use Python v3.9
FROM python:3.9

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
# Copy requirements.txt to ensure dependencies are installed
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Bundle app source
COPY . .

# Expose the port
EXPOSE 3000

CMD [ "python", "main.py" ]
