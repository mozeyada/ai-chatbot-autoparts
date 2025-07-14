# Quick Setup Guide

This guide will help you get the AI Auto Parts Chatbot running in 5 minutes.

## Prerequisites

- **Python 3.8+** installed on your system
- **Internet connection** for API access
- **Terminal/Command Prompt** access

## Step 1: Get Your Free Groq API Key

1. **Visit** [console.groq.com](https://console.groq.com/keys)
2. **Sign up** for a free account (no credit card required)
3. **Click** "Create API Key"
4. **Copy** the key (it starts with `gsk_...`)
5. **Keep it safe** - you'll need it in the next step

## Step 2: Download and Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mozeyada/ai-chatbot-autoparts.git
   cd ai-chatbot-autoparts
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Add your API key**
   
   **Option A: Edit the file**
   - Open `.env` in any text editor
   - Replace `your_groq_api_key_here` with your actual key
   
   **Option B: Command line**
   ```bash
   echo "GROQ_API_KEY=gsk_your_actual_key_here" > .env
   ```

## Step 3: Run the Chatbot

**Easy way (recommended):**
```bash
chmod +x start.sh
./start.sh
```

**Manual way:**
```bash
pip install -r requirements.txt
python chatbot.py
```

**With virtual environment (best practice):**
```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the chatbot
python chatbot.py
```

## Step 4: Access the Interface

1. **Look for this message** in your terminal:
   ```
   📍 Access at: http://localhost:7860
   ```

2. **Open your browser** and go to that URL

3. **Start chatting!** Try these examples:
   - "Honda battery"
   - "Toyota tires"
   - "What are your hours?"

## Having Issues?

### "GROQ_API_KEY environment variable is required"
- ✅ Make sure you created the `.env` file
- ✅ Check your API key is correctly pasted
- ✅ Verify the key starts with `gsk_`

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Port already in use
- The app will automatically find another port
- Check the terminal for the correct URL

### Still stuck?
- Check the [README.md](README.md) for detailed instructions
- Open an [issue on GitHub](https://github.com/mozeyada/ai-chatbot-autoparts/issues)

---

**That's it! You should now have a working AI chatbot for auto parts.**

**Tip:** The chatbot works best when you specify both vehicle make and part type (e.g., "Honda battery" instead of just "battery").