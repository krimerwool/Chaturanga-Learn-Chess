# Use Node.js 18 (LTS) as the base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Build the React app for production
RUN npm run build

# Install serve to serve the built app
RUN npm install -g serve

# Expose port 3000 for the frontend
EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "build", "-l", "3000"]