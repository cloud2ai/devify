# Production Dockerfile for Devify UI
FROM node:22-alpine AS builder

# Set working directory
WORKDIR /app

# Build arguments for configuration
ARG VITE_API_BASE_URL
ARG VITE_EMAIL_DOMAIN=devify.local

# Set as environment variable for build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_EMAIL_DOMAIN=${VITE_EMAIL_DOMAIN}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration for SPA routing
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
