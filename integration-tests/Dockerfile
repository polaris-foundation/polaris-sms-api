FROM python:3.9-slim
ARG PIP_EXTRA_INDEX_URL

WORKDIR /app

# Install dependencies
ADD requirements.txt .
RUN pip install -r requirements.txt

# Add the app
ADD . .

# Engage.
CMD ["behave", "--no-capture"]
