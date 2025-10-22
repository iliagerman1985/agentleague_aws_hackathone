FROM node:20-alpine

WORKDIR /app

# Install wget for health checks
RUN apk add --no-cache wget

# Copy package files first (for better caching)
COPY package.json package-lock.json ./

# Install dependencies first (this layer will be cached if package.json doesn't change)
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# Copy source code (this layer changes more frequently)
COPY . .

# Build the application
RUN --mount=type=cache,target=/root/.npm \
    npm run build

# DON'T remove dev dependencies - vite is needed for preview
# RUN npm prune --omit=dev  # <-- This line was causing the "vite: not found" error

# Expose the port the app runs on
EXPOSE 5888

# Start the application
CMD ["npm", "run", "preview"]