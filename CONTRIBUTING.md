# Contributing to Torrent to Google Drive Bot

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)
   - Relevant logs (remove sensitive info)

### Suggesting Features

1. Check if the feature has been suggested
2. Create a new issue with:
   - Clear description of the feature
   - Use case and benefits
   - Possible implementation approach

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/torrent-to-gdrive-bot.git
cd torrent-to-gdrive-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your test credentials

# Run locally
python main.py
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions focused and small
- Add comments for complex logic

## Testing

Before submitting PR:
1. Test with various torrent types
2. Test file selection UI
3. Verify upload to Google Drive
4. Check error handling
5. Test on multiple Python versions (3.9+)

## Project Structure

```
bot/         - Telegram bot handlers
torrent/     - Torrent client logic
drive/       - Google Drive integration
utils/       - Helper functions and utilities
config/      - Configuration management
```

## Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs when relevant

Examples:
- `Add file size validation before download`
- `Fix progress update message editing error`
- `Refactor rclone upload progress parsing`

## Areas for Contribution

- [ ] Better error handling and recovery
- [ ] Additional torrent client backends
- [ ] Support for other cloud storage providers
- [ ] Web dashboard for monitoring
- [ ] Docker support
- [ ] Unit and integration tests
- [ ] Better progress visualization
- [ ] Support for torrent search
- [ ] Download history and management
- [ ] Multi-language support

## Questions?

Feel free to open an issue for discussion before starting work on major changes.

Thank you for contributing! 🎉
