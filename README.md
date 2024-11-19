# White Analysis

Automated analysis tool for HC White's work using AI models.

## Prerequisites

- Python 3.12+
- uv package manager
- OpenAI API key

## Installation

```bash
uv venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
uv pip install -r requirements.txt
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_key_here  # Linux/Mac
set OPENAI_API_KEY=your_key_here     # Windows
```

Alternatively, use the `.env` file, which will be loaded by the package.

## Usage

1. Place PDF documents in `documents/` folder
2. Create cases in `inputs/cases.json`:
```json
{
    "case1": "Analysis criteria 1",
    "case2": "Analysis criteria 2"
}
```

3. Run analysis:
```bash
whiteanalysis --document-folder documents --output-folder output --model gpt-4
```

## Development

Install dev dependencies:
```bash
uv pip install -e ".[dev]"
pre-commit install
```

## License

[Insert your license choice]