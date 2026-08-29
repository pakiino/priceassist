# Price Assist

## What this does
An AI-powered resale pricing assistant for handheld gaming consoles (Steam
Deck OLED, Nintendo Switch OLED - Tears of the Kingdom Edition, New Nintendo
3DS XL - Hyrule Edition). Upload a photo and it identifies the item and
describes its visible condition using Google's Gemini API, computes a
suggested price from real recent sold-listing data, and generates a
ready-to-post listing title and description.

## How it's organized
- main.py -- the Streamlit app (entry point)
- pricing.py -- computes median/min/max price from sold-listing data
- data/ -- raw_sold_listings_all.csv (sold listings used for pricing),
  active_listings_reference.csv (supporting evidence, not used in the price
  calculation), comps_dataset_template.csv
- tests/ -- unit tests for pricing.py
- test_identify.py, api_key.example.txt -- a standalone script used during
  development to test Gemini identification; not part of the app itself

## Dependencies
See requirements.txt. Install with:

    pip install -r requirements.txt

## How to run
1. Get a free Gemini API key at https://aistudio.google.com/apikey
2. Either set it as an environment variable before launching:
   - Windows PowerShell: `$env:GEMINI_API_KEY="your key here"`
   - macOS/Linux: `export GEMINI_API_KEY="your key here"`

   or leave it unset and paste it into the sidebar text box once the app opens.
3. Run:

       streamlit run main.py

   (On Windows, if `streamlit` isn't recognized as a command, use
   `py -m streamlit run main.py` instead.)

## How to run tests
    python -m unittest discover -s tests -p "test_*.py" -v
