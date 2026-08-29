import os
import streamlit as st
from google import genai
from google.genai import types
from pricing import get_price_stats

st.title("Resale Price Assistant")

# The exact 3 item names as they appear in the pricing data -- used both as
# the AI's closed-choice list and as the dropdown options, so there's never
# a mismatch between what the AI says and what pricing.py can look up.
KNOWN_ITEMS = [
    "Steam Deck OLED",
    "Nintendo Switch OLED - Tears of the Kingdom Edition",
    "New Nintendo 3DS XL - Hyrule Edition",
]

# --- API key: environment variable for local dev, sidebar input as the
#     documented fallback for anyone else running this app ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API key", type="password")

if not api_key:
    st.info("Enter your Gemini API key in the sidebar to get started. "
             "Get a free one at https://aistudio.google.com/apikey")
    st.stop()

client = genai.Client(api_key=api_key)

# --- Step A: photo upload -> auto-identify + auto-describe ---
uploaded_file = st.file_uploader("Upload a photo of your item", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is not None:
    st.image(uploaded_file, width=300)

    # Only call Gemini once per uploaded photo -- not on every rerun caused
    # by editing a field below. We track which file we last processed.
    file_signature = (uploaded_file.name, uploaded_file.size)
    if st.session_state.get("uploaded_signature") != file_signature:
        image_bytes = uploaded_file.getvalue()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=uploaded_file.type)

        prompt_text = (
            "This photo shows a resale handheld gaming console. It is one of the following: "
            + ", ".join(KNOWN_ITEMS) + ".\n"
            "Reply in exactly this format:\n"
            "Line 1: the exact name of the item from the list above, nothing else.\n"
            "Line 2 onward: a short resale listing description (2-4 sentences) based only on what "
            "is visible in the photo, including any visible wear such as scratches, dents, screen "
            "cracks, or discoloration. Do not claim anything about whether it powers on or "
            "functions correctly -- that cannot be determined from a photo."
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[image_part, prompt_text],
        )

        item_name, _, description = response.text.partition("\n")
        st.session_state["identified_name"] = item_name.strip()
        st.session_state["identified_description"] = description.strip()
        st.session_state["uploaded_signature"] = file_signature

    st.subheader("Step 1: Confirm identification")

    # Pre-select whatever the AI guessed; fall back to the first option if
    # its answer somehow doesn't match one of the 3 known items exactly.
    guessed = st.session_state["identified_name"]
    default_index = KNOWN_ITEMS.index(guessed) if guessed in KNOWN_ITEMS else 0

    confirmed_name = st.selectbox("Item (correct if wrong)", KNOWN_ITEMS, index=default_index)
    confirmed_description = st.text_area(
        "Description (edit as needed)",
        value=st.session_state["identified_description"],
    )

    # --- Step B: variant + completeness + accessory notes ---
    st.subheader("Step 2: Confirm details")

    if confirmed_name == "Steam Deck OLED":
        storage_variant = st.selectbox("Storage", ["512GB", "1TB"])
    else:
        storage_variant = "standard"

    completeness = st.radio("Completeness", ["Loose", "CIB"])
    accessory_notes = st.text_area("Accessory notes (optional)", placeholder="e.g. missing charger, includes extra Joy-Con")

    # --- Step C: price lookup ---
    st.subheader("Step 3: Price")
    median_price, min_price, max_price = get_price_stats(confirmed_name, storage_variant, completeness)
    price_col1, price_col2, price_col3 = st.columns(3)
    price_col1.metric("Median", f"${median_price:.2f}")
    price_col2.metric("Min", f"${min_price:.2f}")
    price_col3.metric("Max", f"${max_price:.2f}")

    # --- Step D: urgency presets + editable price ---
    st.subheader("Step 4: Set your price")

    # Reset the suggested price to this item's median whenever the
    # identified item/variant/completeness changes, so an old price from a
    # previous photo doesn't linger.
    pricing_signature = (confirmed_name, storage_variant, completeness)
    if st.session_state.get("pricing_signature") != pricing_signature:
        st.session_state["price"] = median_price
        st.session_state["pricing_signature"] = pricing_signature

    urgency_col1, urgency_col2, urgency_col3 = st.columns(3)
    if urgency_col1.button("Must go ASAP"):
        st.session_state["price"] = min_price
    if urgency_col2.button("No rush"):
        st.session_state["price"] = median_price
    if urgency_col3.button("Want max profit"):
        st.session_state["price"] = max_price

    final_price = st.number_input("Your listing price ($)", key="price", step=1.0)

    pct_vs_median = (final_price - median_price) / median_price * 100
    st.caption(f"{pct_vs_median:+.1f}% vs. median")

    # --- Step E: generate final listing (title + description) ---
    st.subheader("Step 5: Generate listing")
    if st.button("Generate listing"):
        listing_prompt = (
            "Write a resale listing for the following item:\n"
            f"Item: {confirmed_name} ({storage_variant})\n"
            f"Completeness: {completeness}\n"
            f"Condition notes: {confirmed_description}\n"
            f"Accessory notes: {accessory_notes or 'none provided'}\n\n"
            "Reply in exactly this format:\n"
            "Line 1: a short, appealing listing title (under 80 characters). "
            "Do not include the price in the title.\n"
            "Line 2 onward: a 3-5 sentence listing description a seller could post as-is, "
            "incorporating the completeness, condition notes, and accessory notes above. "
            "Do not invent details not provided above, and do not mention the exact price "
            "in the description -- it is shown separately."
        )
        listing_response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[listing_prompt],
        )
        listing_title, _, listing_description = listing_response.text.partition("\n")
        st.session_state["listing_title"] = listing_title.strip()
        st.session_state["listing_description"] = listing_description.strip()

    # --- Step F: final output ---
    if "listing_title" in st.session_state:
        st.subheader("Final listing")
        st.subheader(st.session_state["listing_title"])
        st.write(st.session_state["listing_description"])
        st.metric("Asking price", f"${final_price:.2f}")
