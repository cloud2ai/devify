#!/bin/bash

# Devify UI Start Script

echo "🚀 Starting Devify UI Development Server..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Start development server
echo "🔥 Starting Vite development server..."
echo "📱 Open your browser at: http://localhost:3000"
echo "🔗 API will be proxied to: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev
