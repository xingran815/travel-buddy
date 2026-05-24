# Travel Buddy

[English](README.md) | [Turkce](README.tr.md)

A command-line tool that helps you plan trips by summarizing YouTube travel videos, finding the best-rated places, and generating travel itineraries — all powered by AI.

## Features

- **Summarize YouTube Videos** — Paste a YouTube link and get a translated summary in English or Turkish
- **Get Place Recommendations** — Find top-rated restaurants, attractions, and more using Google Maps data and AI-powered ranking
- **Create Travel Plan [Beta]** — Generate a multi-day itinerary combining video insights and place recommendations *(this feature is functional but has not been extensively tested)*

## Prerequisites

You need three things before you start: **Python**, **ffmpeg**, and **API keys**.

### Step 1: Install Python and ffmpeg

<details>
<summary><strong>macOS</strong> (click to expand)</summary>

Open the **Terminal** app (search for "Terminal" in Spotlight with Cmd+Space).

**Install Xcode Command Line Tools** (includes git and build tools):

```bash
xcode-select --install
```

A dialog will pop up — click "Install" and wait for it to finish.

**Install Homebrew** (a package manager for macOS):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions. When it finishes, it may ask you to run two commands to add Homebrew to your PATH — copy and run them.

**Install Python and ffmpeg:**

```bash
brew install python ffmpeg
```

**Verify everything works:**

```bash
python3 --version
ffmpeg -version
```

You should see version numbers printed for both.

</details>

<details>
<summary><strong>Windows</strong> (click to expand)</summary>

**Install Python:**

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3 installer
3. **Important:** Check the box that says **"Add Python to PATH"** before clicking Install
4. Click "Install Now"

**Install ffmpeg:**

Open **Command Prompt** (search for "cmd" in the Start menu) and run:

```cmd
winget install ffmpeg
```

If `winget` is not available, download ffmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add it to your system PATH.

**Verify everything works:**

```cmd
python --version
ffmpeg -version
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong> (click to expand)</summary>

Open a terminal and run:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg
```

**Verify:**

```bash
python3 --version
ffmpeg -version
```

</details>

### Step 2: Get API Keys

You need at least one API key to use this tool. Which keys you need depends on the features you want:

| Feature | Keys Required |
|---------|---------------|
| Summarize YouTube Videos | LLM API key (OpenAI, Anthropic, or Ollama) |
| Get Place Recommendations | LLM API key + Google Maps API key |
| Create Travel Plan | LLM API key + Google Maps API key |

#### Option A: OpenAI (default)

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create an account or sign in
3. Click **"Create new secret key"**
4. Copy the key — you will need it in the next step

> OpenAI charges per usage. For typical use, expect a few cents per video summary and a few cents per recommendation query.

#### Option B: Anthropic

1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Create an account or sign in
3. Click **"Create Key"**
4. Copy the key

#### Option C: Ollama (free, runs locally)

Ollama runs AI models on your own computer — no API key needed, completely free.

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Open a terminal and run: `ollama pull llama3.1`
3. Keep Ollama running in the background when using Travel Buddy

#### Google Maps API Key

Required for place recommendations and travel plans.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Go to **APIs & Services > Library**
4. Search for and enable **Places API**
5. Search for and enable **Geocoding API**
6. Go to **APIs & Services > Credentials**
7. Click **"Create Credentials" > "API key"**
8. Copy the key

> Google gives you $200/month in free credits, which covers typical personal use.

## Installation

### macOS / Linux

```bash
git clone https://github.com/xingran/travel-buddy.git
cd travel-buddy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

```cmd
git clone https://github.com/xingran/travel-buddy.git
cd travel-buddy
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> If using Anthropic as your LLM provider, also install: `pip install anthropic`

### Configure Your API Keys

```bash
cp .env.example .env
```

On Windows, use `copy .env.example .env` instead.

Open the `.env` file in any text editor and fill in your API keys:

```env
LLM_API_KEY=sk-your-openai-key-here
GOOGLE_MAPS_API_KEY=AIza-your-google-key-here
```

See `.env.example` for all available options, including Anthropic and Ollama configuration.

## Usage

### Interactive Menu (recommended)

The easiest way to use Travel Buddy:

```bash
python main.py
```

This opens a menu where you can choose what to do:

```
1. Summarize YouTube Video
2. Get Place Recommendations
3. Create Travel Plan [Beta]
4. Settings
q. Quit
```

Just follow the prompts — no command-line experience needed.

### CLI Commands

For advanced users, you can use commands directly:

**Summarize a video:**

```bash
python main.py summarize "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Get place recommendations:**

```bash
# Basic: top 5 restaurants in a region
python main.py recommend "Istanbul" --type restaurant --top 5

# By category: food + sights
python main.py recommend "Paris" --category food,sights --top 3

# With preferences
python main.py recommend "Tokyo" --type restaurant --cuisine japanese --budget 50 --profile foodie
```

**Create a travel plan:**

```bash
python main.py plan "Istanbul" --budget 500 --days 3 --preferences "history,food"
```

### Changing Language

- **In the menu:** Select "Settings" and choose your language
- **Via command line:** Add `--lang en` or `--lang tr`
- **Permanently:** Set `APP_LANG=en` or `APP_LANG=tr` in your `.env` file

## Configuration

All settings are in the `.env` file. Here are the key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | *(required)* | Your AI provider's API key |
| `LLM_PROVIDER` | `openai` | AI provider: `openai`, `anthropic`, or `ollama` |
| `LLM_MODEL` | `gpt-4o` | Model to use |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API endpoint |
| `GOOGLE_MAPS_API_KEY` | *(required for recommendations)* | Google Maps API key |
| `APP_LANG` | `tr` | Interface language: `en` or `tr` |

## Project Structure

```
travel-buddy/
  main.py              # Entry point (CLI commands + interactive menu)
  app/
    cli/               # CLI argument parsing helpers
    i18n/              # Translations (English + Turkish)
    llm/               # AI provider abstraction (OpenAI, Anthropic, Ollama)
    places/            # Google Places API caching layer
    planner/           # Travel itinerary generator
    profile/           # User preference persistence
    reviews/           # Place recommendation engine (scoring, ranking)
    ui/                # Interactive menu and display formatting
    youtube/           # YouTube audio download and transcription
  tests/               # Test suite
```

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run lint: `pylint app main.py`
6. Submit a pull request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
