FROM node:18-alpine

WORKDIR /app

# Install Chromium and dependencies
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy application files
COPY . .

# Set Puppeteer to use installed Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Create directories
RUN mkdir -p screenshots data channel_data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Install curl for health check
RUN apk add --no-cache curl

# Default command
CMD ["node", "api_server.js"]