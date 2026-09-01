# Price Assist

## What this does
An AI-powered resale pricing assistant for handheld gaming consoles (Steam
Deck OLED, Nintendo Switch OLED - Tears of the Kingdom Edition, New Nintendo
3DS XL - Hyrule Edition). Upload a photo and it identifies the item and
describes its visible condition using Google's Gemini API, computes a
suggested price from real recent sold-listing data, and generates a
ready-to-post listing title and description.

## Condition-adjustment methodology
Beyond the base price (median of matching sold listings), the app applies
optional deductions for common defects: broken/cracked screen, missing
charger, stick/Joy-Con drift, and heavy cosmetic wear.

These deductions are heuristic estimates, not fixed percentages published
by any marketplace. They're derived from observable repair costs, repair
complexity, marketplace condition/eligibility requirements, and the added
condition sensitivity of collectible special-edition hardware. Sources:
[iFixit Steam Deck OLED parts](https://www.ifixit.com/Parts/Steam_Deck_OLED),
[iFixit thumbstick replacement guide](https://www.ifixit.com/Guide/Steam%2BDeck%2BOLED%2BRight%2BThumbstick%2BReplacement/168609),
[Nintendo Joy-Con drift support](https://en-americas-support.nintendo.com/app/answers/detail/a_id/46903),
[Swappa listing criteria](https://swappa.com/faq/answer/listing-device-criteria).

Deductions are applied multiplicatively per defect, not stacked additively,
to avoid unrealistic combined penalties.

## How it's organized
- main.py -- the Streamlit app (entry point)
- pricing.py -- computes median/min/max price from sold-listing data
- data/ -- raw_sold_listings_all.csv (sold listings used for pricing),
  active_listings_reference.csv (supporting evidence, not used in the price
  calculation), comps_dataset_template.csv
- tests/ -- unit tests for pricing.py

## How to run -- Windows
1. Get a free Gemini API key: https://aistudio.google.com/apikey
2. Open Command Prompt in this folder.
3. Install dependencies:

       pip install -r requirements.txt

   If `pip` isn't recognized, try instead: `py -m pip install -r requirements.txt`

4. (Optional) Set your API key as an environment variable so you don't have
   to paste it in every time:

       $env:GEMINI_API_KEY="your key here"

   Skipping this is fine -- you can paste the key into the sidebar text box
   once the app opens instead.

5. Run the app:

       streamlit run main.py

   If `streamlit` isn't recognized, try these instead, in order, until one
   works:

       py -m streamlit run main.py
       python -m streamlit run main.py
       python3 -m streamlit run main.py

   If none of these work even from a brand-new Command Prompt window,
   Python isn't installed or isn't on your PATH -- install it from
   https://www.python.org/downloads/ and check "Add python.exe to PATH"
   during setup.

6. A browser tab opens automatically at http://localhost:8501.

## How to run -- macOS / Linux
1. Get a free Gemini API key: https://aistudio.google.com/apikey
2. Open Terminal in this folder.
3. Install dependencies:

       pip install -r requirements.txt

   If `pip` isn't recognized, try instead: `python3 -m pip install -r requirements.txt`

4. (Optional) Set your API key as an environment variable so you don't have
   to paste it in every time:

       export GEMINI_API_KEY="your key here"

   Skipping this is fine -- you can paste the key into the sidebar text box
   once the app opens instead.

5. Run the app:

       streamlit run main.py

   If `streamlit` isn't recognized, try instead: `python3 -m streamlit run main.py`

6. A browser tab opens automatically at http://localhost:8501.

## How to run tests
    python -m unittest discover -s tests -p "test_*.py" -v
