#!/bin/bash
# Shrimp Agent v5.0.0 - macOS Setup Script
# Architecture: Agent-based (backend_operator, virtual_human, shared)

echo "🦐 Shrimp Agent v5.0.0 - macOS Setup"
echo "===================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker not found"
    echo "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo "✅ Docker: $(docker --version)"

# Check docker-compose
if command -v docker-compose &> /dev/null; then
    echo "✅ Compose: $(docker-compose --version)"
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    echo "✅ Compose: $(docker compose version)"
    COMPOSE_CMD="docker compose"
else
    echo "❌ Error: docker-compose not found"
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your API_KEY"
        echo "   Command: nano .env"
        echo ""
    else
        echo "⚠️  Warning: .env.example not found"
    fi
else
    echo "✅ .env file exists"
fi

# Create directories
echo ""
echo "📁 Checking directories..."
if [ ! -d "../workspace" ]; then
    mkdir -p ../workspace
    echo "✅ Created ../workspace/"
fi
if [ ! -d "../downloads" ]; then
    mkdir -p ../downloads
    echo "✅ Created ../downloads/"
fi
if [ ! -d "../knowledge" ]; then
    mkdir -p ../knowledge
    echo "✅ Created ../knowledge/"
    echo "   💡 Tip: Place your knowledge files in ../knowledge/{knowledge_id}/"
fi
echo "✅ Directories ready"

# Check agent files (New Architecture v5.0.0)
echo ""
echo "🔍 Checking agent files..."
AGENT_FILES=(
    "../agent/backend_operator/api.py"
    "../agent/virtual_human/api.py"
    "../agent/shared/sse_events.py"
    "../session/session_store.py"
    "../frontend/templates/index.html"
    "../frontend/static/js/chat.js"
)
MISSING_FILES=()

for file in "${AGENT_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo "❌ ERROR: Agent files not found!"
    echo ""
    echo "Missing files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "Expected directory structure:"
    echo "  agtshrimp/"
    echo "  ├── agent/"
    echo "  │   ├── backend_operator/  # Agent API"
    echo "  │   ├── virtual_human/     # VH Agent"
    echo "  │   └── shared/            # Shared modules"
    echo "  ├── session/               # Session management"
    echo "  ├── frontend/              # Web UI"
    echo "  ├── setup/                 # You are here"
    echo "  ├── workspace/             # Will be created"
    echo "  ├── downloads/             # Will be created"
    echo "  └── knowledge/             # Knowledge base"
    echo ""
    echo "Solution:"
    echo "1. Use Git clone (recommended):"
    echo "   git clone https://github.com/srjiang/agtshrimp.git"
    echo "   cd agtshrimp"
    echo "   git checkout dev"
    echo ""
    echo "2. Or download ZIP from dev branch:"
    echo "   https://github.com/srjiang/agtshrimp/archive/refs/heads/dev.zip"
    echo ""
    
    exit 1
fi

echo "✅ All agent files found"

# Done
echo ""
echo "===================================="
echo "✅ Setup Complete!"
echo ""
echo "🚀 Next steps:"
echo "1. Edit .env file (add your API_KEY)"
echo "2. $COMPOSE_CMD up -d --build"
echo ""
echo "🌐 Web UI: http://localhost:5000"
echo "🔌 Agent API: http://localhost:8000"
echo "===================================="
