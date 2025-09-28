.PHONY: help dev dev-backend dev-frontend build-frontend clean install setup langgraph-setup langgraph-install

# Default target
help:
	@echo "Available commands:"
	@echo "  make dev              - Start both backend and frontend in development mode"
	@echo "  make dev-backend      - Start only the backend server"
	@echo "  make dev-frontend     - Start only the frontend development server"
	@echo "  make build-frontend   - Build the frontend for production"
	@echo "  make clean            - Clean up generated files"
	@echo "  make install          - Install dependencies for both projects"
	@echo "  make setup            - Initial setup for both projects"
	@echo ""
	@echo "Backend commands:"
	@echo "  make langgraph-setup  - Setup backend server environment"
	@echo "  make langgraph-install - Install backend dependencies"

# Development - Start both services

# Start backend server
dev-backend:
	@echo "🔧 Starting backend server..."
	@echo "This is not reloadable. Restart this command to apply changes."
	cd mock-backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Start frontend development server
dev-frontend:
	@echo "⚛️  Starting frontend development server..."
	@sleep 2 && bun run dev

# Start frontend and backend server
dev:
	@echo "🚀 Starting frontend and backend server..."
	@echo "🔧 Backend will be available at: http://localhost:8000"
	@echo "🌐 Frontend will be available at: http://localhost:3000"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@make -j2 dev-backend dev-frontend


# Build frontend for production
build-frontend:
	@echo "📦 Building frontend for production..."
	bun run build

# Clean up generated files
clean:
	@echo "🧹 Cleaning up generated files..."
	rm -rf .next
	rm -rf node_modules
	rm -rf mock-backend/.venv
	rm -f bun.lock

# Install dependencies for both projects
install:
	@echo "📥 Installing dependencies..."
	@echo "Installing frontend dependencies..."
	bun install
	@echo "Installing backend dependencies..."
	cd mock-backend && uv sync

# Initial setup
setup: install langgraph-setup
	@echo "⚙️  Setting up environment..."
	@if [ ! -f .env.local ]; then \
		echo "Creating .env.local from .env.example..."; \
		cp .env.example .env.local 2>/dev/null || echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000" > .env.local; \
	fi
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Configure your environment variables in .env.local"
	@echo "2. Edit mock-backend/.env with your credentials if needed"
	@echo "3. Run 'make dev' to start both services"
	@echo "4. Open http://localhost:3000 in your browser"

# Stop all running services
stop:
	@echo "🛑 Stopping all services..."
	-pkill -f "next dev" || true
	-pkill -f "bun run dev" || true
	-pkill -f "uvicorn main:app" || true
	@echo "✅ All services stopped"

# Show status of running services
status:
	@echo "📊 Service Status:"
	@pgrep -f "uvicorn main:app" > /dev/null && echo "✅ Backend: Running (PID: $$(pgrep -f "uvicorn main:app"))" || echo "❌ Backend: Not running"
	@pgrep -f "next dev\|bun run dev" > /dev/null && echo "✅ Frontend: Running (PID: $$(pgrep -f "next dev\|bun run dev"))" || echo "❌ Frontend: Not running"

# Development with logs
dev-logs:
	@echo "🚀 Starting services with detailed logging..."
	@echo "Backend logs:" > backend.log
	@echo "Frontend logs:" > frontend.log
	@make -j2 dev-backend-logs dev-frontend-logs

dev-backend-logs:
	cd mock-backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | tee ../backend.log

dev-frontend-logs:
	bun run dev 2>&1 | tee frontend.log


langgraph-setup:
	@echo "⚙️  Setting up backend server..."
	@if [ ! -f mock-backend/.env ]; then \
		echo "Creating .env from env.sample..."; \
		cp mock-backend/env.sample mock-backend/.env; \
		echo "⚠️  Please edit mock-backend/.env with your Azure OpenAI credentials"; \
	fi
	@echo "✅ Backend setup complete!"

langgraph-install:
	@echo "📥 Installing backend dependencies..."
	cd mock-backend && uv sync
	@echo "✅ Backend dependencies installed"