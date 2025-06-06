#!/usr/bin/env python3
"""
LLM Phone Feedback System - Setup Script
=========================================

This script automates the setup process for the LLM Phone Feedback System.
It checks dependencies, sets up virtual environments, and configures the development environment.

Usage:
    python setup.py --help
    python setup.py --dev          # Development setup
    python setup.py --prod         # Production setup
    python setup.py --check        # Check dependencies only
"""

import os
import sys
import subprocess
import platform
import argparse
import shutil
from pathlib import Path

class SetupManager:
    def __init__(self):
        self.system = platform.system().lower()
        self.project_root = Path(__file__).parent
        self.server_dir = self.project_root / "server"
        self.venv_path = self.server_dir / "venv"
        
    def log(self, message, level="INFO"):
        """Simple logging function"""
        colors = {
            "INFO": "\033[94m",  # Blue
            "SUCCESS": "\033[92m",  # Green
            "WARNING": "\033[93m",  # Yellow
            "ERROR": "\033[91m",  # Red
            "RESET": "\033[0m"  # Reset
        }
        color = colors.get(level, colors["INFO"])
        print(f"{color}[{level}]{colors['RESET']} {message}")
    
    def run_command(self, command, cwd=None, check=True):
        """Run shell command with error handling"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {command}", "ERROR")
            self.log(f"Error: {e.stderr}", "ERROR")
            return None
    
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        self.log("Checking system dependencies...")
        
        dependencies = {
            "python": ["python", "--version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"],
            "git": ["git", "--version"]
        }
        
        missing = []
        for name, command in dependencies.items():
            result = self.run_command(" ".join(command), check=False)
            if result and result.returncode == 0:
                version = result.stdout.strip()
                self.log(f"✓ {name}: {version}", "SUCCESS")
            else:
                self.log(f"✗ {name}: Not found", "ERROR")
                missing.append(name)
        
        if missing:
            self.log(f"Missing dependencies: {', '.join(missing)}", "ERROR")
            self.log("Please install missing dependencies before continuing.", "ERROR")
            return False
        
        return True
    
    def setup_python_environment(self):
        """Setup Python virtual environment and install dependencies"""
        self.log("Setting up Python environment...")
        
        # Create virtual environment
        if not self.venv_path.exists():
            self.log("Creating virtual environment...")
            result = self.run_command(f"python -m venv {self.venv_path}")
            if not result:
                return False
        else:
            self.log("Virtual environment already exists", "WARNING")
        
        # Determine activation script path
        if self.system == "windows":
            activate_script = self.venv_path / "Scripts" / "activate.bat"
            pip_executable = self.venv_path / "Scripts" / "pip.exe"
        else:
            activate_script = self.venv_path / "bin" / "activate"
            pip_executable = self.venv_path / "bin" / "pip"
        
        # Install requirements
        self.log("Installing Python dependencies...")
        requirements_file = self.server_dir / "requirements.txt"
        if requirements_file.exists():
            result = self.run_command(f"{pip_executable} install -r {requirements_file}")
            if result:
                self.log("Python dependencies installed successfully", "SUCCESS")
            return result is not None
        else:
            self.log("requirements.txt not found", "ERROR")
            return False
    
    def setup_node_environment(self):
        """Setup Node.js environment and install dependencies"""
        self.log("Setting up Node.js environment...")
        
        package_json = self.project_root / "package.json"
        if not package_json.exists():
            self.log("package.json not found", "ERROR")
            return False
        
        # Install Node dependencies
        self.log("Installing Node.js dependencies...")
        result = self.run_command("npm install")
        if result:
            self.log("Node.js dependencies installed successfully", "SUCCESS")
            return True
        return False
    
    def setup_environment_file(self):
        """Setup environment configuration file"""
        self.log("Setting up environment configuration...")
        
        env_template = self.project_root / ".env.template"
        env_file = self.project_root / ".env"
        
        if env_template.exists() and not env_file.exists():
            shutil.copy(env_template, env_file)
            self.log("Created .env file from template", "SUCCESS")
            self.log("⚠️  Please edit .env file with your actual API keys and configuration", "WARNING")
        elif env_file.exists():
            self.log(".env file already exists", "WARNING")
        else:
            self.log(".env.template not found", "ERROR")
            return False
        
        return True
    
    def setup_git_hooks(self):
        """Setup git hooks for development"""
        self.log("Setting up git hooks...")
        
        hooks_dir = self.project_root / ".git" / "hooks"
        if not hooks_dir.exists():
            self.log("Git repository not initialized", "WARNING")
            return True
        
        # Create pre-commit hook
        pre_commit_hook = hooks_dir / "pre-commit"
        hook_content = """#!/bin/sh
# LLM Phone Feedback System - Pre-commit Hook

echo "Running pre-commit checks..."

# Check Python code style
echo "Checking Python code style..."
if command -v flake8 >/dev/null 2>&1; then
    flake8 server/ --max-line-length=88 --exclude=venv/,__pycache__/
    if [ $? -ne 0 ]; then
        echo "Python code style check failed!"
        exit 1
    fi
fi

# Check JavaScript/React code
echo "Checking JavaScript code..."
npm run lint
if [ $? -ne 0 ]; then
    echo "JavaScript code style check failed!"
    exit 1
fi

echo "Pre-commit checks passed!"
"""
        
        with open(pre_commit_hook, "w") as f:
            f.write(hook_content)
        
        # Make executable
        os.chmod(pre_commit_hook, 0o755)
        self.log("Git pre-commit hook installed", "SUCCESS")
        
        return True
    
    def create_start_script(self):
        """Create convenient start script"""
        self.log("Creating start script...")
        
        if self.system == "windows":
            script_name = "start_dev.bat"
            script_content = """@echo off
echo Starting LLM Phone Feedback System Development Environment...
echo.

REM Start MongoDB (if installed locally)
echo Starting MongoDB...
start /B mongod

REM Wait a moment for MongoDB to start
timeout /t 3 /nobreak > nul

REM Start backend server
echo Starting backend server...
cd server
call venv\\Scripts\\activate
start /B python main.py
cd ..

REM Start frontend
echo Starting frontend...
start /B npm start

REM Start ngrok (if available)
echo Starting ngrok...
start /B ngrok http 8000

echo.
echo All services started!
echo Frontend: http://localhost:3000
echo Backend: http://localhost:8000
echo.
pause
"""
        else:
            script_name = "start_dev.sh"
            script_content = """#!/bin/bash
echo "Starting LLM Phone Feedback System Development Environment..."
echo

# Start MongoDB (if installed locally)
echo "Starting MongoDB..."
mongod --fork --logpath /tmp/mongodb.log || echo "MongoDB already running or not installed locally"

# Wait a moment for MongoDB to start
sleep 3

# Start backend server
echo "Starting backend server..."
cd server
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Start frontend
echo "Starting frontend..."
npm start &
FRONTEND_PID=$!

# Start ngrok (if available)
echo "Starting ngrok..."
ngrok http 8000 &
NGROK_PID=$!

echo
echo "All services started!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID $NGROK_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
"""
        
        script_path = self.project_root / script_name
        with open(script_path, "w") as f:
            f.write(script_content)
        
        if self.system != "windows":
            os.chmod(script_path, 0o755)
        
        self.log(f"Start script created: {script_name}", "SUCCESS")
        return True
    
    def development_setup(self):
        """Complete development environment setup"""
        self.log("=== LLM Phone Feedback System - Development Setup ===", "INFO")
        
        steps = [
            ("Check dependencies", self.check_dependencies),
            ("Setup Python environment", self.setup_python_environment),
            ("Setup Node.js environment", self.setup_node_environment),
            ("Setup environment file", self.setup_environment_file),
            ("Setup git hooks", self.setup_git_hooks),
            ("Create start script", self.create_start_script)
        ]
        
        for step_name, step_function in steps:
            self.log(f"Step: {step_name}")
            if not step_function():
                self.log(f"Setup failed at step: {step_name}", "ERROR")
                return False
            print()
        
        self.log("=== Setup completed successfully! ===", "SUCCESS")
        self.log("Next steps:", "INFO")
        self.log("1. Edit .env file with your API keys", "INFO")
        self.log("2. Start MongoDB service", "INFO")
        self.log("3. Run the start script to launch all services", "INFO")
        
        if self.system == "windows":
            self.log("4. Execute: start_dev.bat", "INFO")
        else:
            self.log("4. Execute: ./start_dev.sh", "INFO")
        
        return True
    
    def production_setup(self):
        """Production environment setup"""
        self.log("=== Production Setup ===", "INFO")
        self.log("Production setup not implemented yet", "WARNING")
        return False

def main():
    parser = argparse.ArgumentParser(description="LLM Phone Feedback System Setup")
    parser.add_argument("--dev", action="store_true", help="Setup development environment")
    parser.add_argument("--prod", action="store_true", help="Setup production environment")
    parser.add_argument("--check", action="store_true", help="Check dependencies only")
    
    args = parser.parse_args()
    
    setup = SetupManager()
    
    if args.check:
        setup.check_dependencies()
    elif args.dev:
        setup.development_setup()
    elif args.prod:
        setup.production_setup()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 