# Contributing to AI Auto Parts Chatbot

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/mozeyada/ai-chatbot-autoparts.git
   cd ai-chatbot-autoparts
   ```
3. **Set up the development environment**:
   ```bash
   cp .env.example .env
   # Add your Groq API key
   pip install -r requirements.txt
   ```

## 🧪 Running Tests

Before submitting changes, ensure all tests pass:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_search.py -v
python -m pytest tests/test_lead_capture.py -v
```

## 📝 Code Style

- **Python**: Follow PEP 8 guidelines
- **Comments**: Use docstrings for functions and classes
- **Imports**: Group imports (standard library, third-party, local)
- **Line Length**: Maximum 100 characters

## 🔧 Development Areas

### High Priority
- **New Vehicle Makes**: Add support for additional car manufacturers
- **Part Categories**: Expand inventory categories and synonyms
- **Language Support**: Multi-language FAQ and responses
- **Performance**: Optimize search algorithms and response times

### Medium Priority
- **UI Enhancements**: Improve Gradio interface components
- **Analytics**: Add conversation analytics and insights
- **Integration**: API endpoints for external systems
- **Documentation**: Expand technical documentation

## 📊 Data Contributions

### Adding New Parts
1. Update `data/products.csv` with proper format
2. Add category synonyms to `data/category_synonyms.csv`
3. Update tests to cover new parts

### FAQ Updates
1. Add entries to `data/faq.json`
2. Include keywords for better matching
3. Test FAQ responses

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment**: Python version, OS, dependencies
- **Steps to reproduce**: Clear, numbered steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Screenshots**: If applicable

## ✨ Feature Requests

For new features, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and business value
3. **Provide examples** of expected behavior
4. **Consider implementation** complexity

## 🔄 Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation if needed

3. **Test your changes**:
   ```bash
   python -m pytest tests/ -v
   ```

4. **Commit with clear messages**:
   ```bash
   git commit -m "Add: New vehicle make support for Tesla"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated (if applicable)
- [ ] No sensitive data in commits
- [ ] Clear commit messages
- [ ] PR description explains changes

## 🏗️ Architecture Guidelines

### Hybrid Design Principles
- **Deterministic data**: Never let LLM invent SKUs, prices, or policies
- **Tool-first**: Use CSV/JSON for business logic, LLM for natural language
- **Fail-safe**: System works even if LLM is unavailable

### Code Organization
- **chatbot.py**: Main application logic
- **data/**: Business data files
- **tests/**: Comprehensive test coverage
- **Separation of concerns**: Clear boundaries between components

## 🤝 Community Guidelines

- **Be respectful**: Treat all contributors with respect
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Allow time for review and discussion
- **Be collaborative**: Work together to improve the project

## 📞 Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Documentation**: Check README.md and code comments

## 🙏 Recognition

Contributors will be recognized in:
- **README.md**: Acknowledgments section
- **Release notes**: Major contributions highlighted
- **GitHub**: Contributor statistics and graphs

---

**Thank you for contributing to AI Auto Parts Chatbot!** 🚀