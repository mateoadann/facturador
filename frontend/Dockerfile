FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Expose port
EXPOSE 5173

# Start dev server
CMD ["npm", "run", "dev"]
