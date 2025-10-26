# WhisperNinja Installation Guide

## Quick Start

### 1. Install from source (Development)

```bash
# Navigate to the project directory
cd /Users/todorov/Documents/coding/call-copilot

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### 2. Install dependencies only

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
# Using the installed script
whisperninja

# Or run directly
python WhisperNinja/main.py
```

## Building Distribution Packages

### macOS App Bundle (py2app)

```bash
# Install build dependencies
pip install -e ".[build]"

# Build macOS app bundle
python setup.py py2app
```

### Executable (PyInstaller)

```bash
# Install build dependencies
pip install -e ".[build]"

# Build executable
pyinstaller WhisperNinja/main.py --name WhisperNinja
```

## Development Setup

### 1. Install development dependencies

```bash
pip install -e ".[dev]"
```

### 2. Set up pre-commit hooks

```bash
pre-commit install
```

### 3. Run tests

```bash
pytest
```

### 4. Code formatting

```bash
black WhisperNinja/
flake8 WhisperNinja/
mypy WhisperNinja/
```

## System Requirements

- **Python**: 3.9 or higher
- **macOS**: 10.15 (Catalina) or higher
- **Audio**: Microphone access required
- **Accessibility**: Required for global hotkeys

## Permissions Required

WhisperNinja requires the following macOS permissions:

1. **Microphone Access**: For audio recording
2. **Accessibility**: For global hotkey detection
3. **Input Monitoring**: For keyboard event handling

Grant these permissions in:
`System Preferences > Security & Privacy > Privacy`

## Troubleshooting

### Common Issues

1. **"keyboard library not available"**
   ```bash
   pip install keyboard
   ```

2. **Audio recording issues**
   - Check microphone permissions
   - Verify audio device is working

3. **Hotkey not working**
   - Check accessibility permissions
   - Try a different hotkey (F3, F4, etc.)

4. **Caps Lock crashes**
   - This should be fixed in the latest version
   - If still occurring, try installing the `keyboard` library

### Getting Help

- Check the [Issues](https://github.com/whisperninja/whisperninja/issues) page
- Create a new issue with:
  - macOS version
  - Python version
  - Error messages
  - Steps to reproduce
