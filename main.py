import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from pricing import get_price_stats, get_recent_listings

st.title("Resale Price Assistant")

# The exact 3 item names as they appear in the pricing data -- used both as
# the AI's closed-choice list and as the dropdown options, so there's never
# a mismatch between what the AI says and what pricing.py can look up.
KNOWN_ITEMS = [
    "Steam Deck OLED",
    "Nintendo Switch OLED - Tears of the Kingdom Edition",
    "New Nintendo 3DS XL - Hyrule Edition",
]

# Condition-adjustment percentages below are heuristic estimates, not
# published marketplace deduction schedules. Derived from repair/replacement
# cost and functional-defect signals (iFixit part/repair data for Steam Deck
# OLED screens, AC adapters, and thumbsticks; Nintendo's own Joy-Con drift
# and physical-damage support pages; Swappa's listing-eligibility rules
# excluding cracked/nonfunctional devices) plus added collector-condition
# sensitivity for the special-edition Switch and 3DS XL. Applied
# multiplicatively per defect, not stacked additively, to avoid unrealistic
# combined penalties (e.g. -50% screen and -30% wear = base x 0.50 x 0.70,
# not -80%).
CONDITION_MULTIPLIERS = {
    "Steam Deck OLED": {"screen": 0.60, "charger": 0.90, "drift": 0.85, "wear": 0.85},
    "Nintendo Switch OLED - Tears of the Kingdom Edition": {"screen": 0.55, "charger": 0.90, "drift": 0.80, "wear": 0.80},
    "New Nintendo 3DS XL - Hyrule Edition": {"screen": 0.50, "charger": 0.95, "drift": 0.80, "wear": 0.70},
}

# Item-specific drift terminology so the checkbox reads naturally for each
# console (Steam Deck's analog sticks vs. detachable Joy-Con vs. the 3DS's
# Circle Pad / C-Stick).
DRIFT_LABELS = {
    "Steam Deck OLED": "Analog stick drift",
    "Nintendo Switch OLED - Tears of the Kingdom Edition": "Joy-Con drift",
    "New Nintendo 3DS XL - Hyrule Edition": "Circle Pad / C-Stick drift or input fault",
}

# Real eBay active-listing snapshot (manually collected Aug 28 2026, not
# live). Used only when the user picks "Active eBay listings average" below
# -- otherwise it's reference/context only.
active_listings_df = pd.read_csv("data/active_listings_reference.csv")


def get_active_listing_stats(item, storage_variant):
    """Average/min/max computed from ALL matching active-listing rows.
    Not filtered by completeness -- this dataset only has a condition_label
    (New/Open-box/Pre-owned), not the Loose/CIB scale the sold data uses.
    Tends to run higher than sold-data stats, since overpriced items that
    haven't sold yet stay visible on eBay longer than fairly-priced ones.
    """
    matches = active_listings_df[
        (active_listings_df["item"] == item)
        & (active_listings_df["storage_variant"] == storage_variant)
    ]
    if matches.empty:
        return None
    return matches["price_usd"].mean(), matches["price_usd"].min(), matches["price_usd"].max()


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

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[image_part, prompt_text],
            )
        except Exception:
            st.error("Could not reach Gemini right now -- you may have run out of your daily Gemini API quota. Try again later.")
            st.stop()

        item_name, _, description = response.text.partition("\n")
        st.session_state["identified_name"] = item_name.strip()
        st.session_state["identified_description"] = description.strip()
        st.session_state["uploaded_signature"] = file_signature

        # Reset the detail selections too, so a new photo never inherits a
        # stale storage/completeness choice left over from a previous item.
        st.session_state["storage_variant_widget"] = "512GB"
        st.session_state["completeness_widget"] = "Loose"
        st.session_state["broken_screen_widget"] = False
        st.session_state["stick_drift_widget"] = False
        st.session_state["heavy_wear_widget"] = False

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
        storage_variant = st.selectbox("Storage", ["512GB", "1TB"], key="storage_variant_widget")
    else:
        storage_variant = "standard"

    completeness = st.radio("Completeness", ["Loose", "CIB"], key="completeness_widget")
    included_accessories = st.multiselect(
        "Included accessories",
        ["Charger / AC adapter", "Carrying case", "SD card", "Extra controller / Joy-Con"],
    )
    other_accessory_notes = st.text_area(
        "Other notes (optional)",
        placeholder="e.g. missing charger, includes rare box art",
    )
    accessory_notes = ", ".join(
        included_accessories + ([other_accessory_notes] if other_accessory_notes else [])
    )

    # --- Step C: price lookup ---
    st.subheader("Step 3: Price")
    pricing_basis = st.radio(
        "Pricing basis",
        ["Sold data (recommended)", "Active eBay listings average"],
        help=(
            "Sold data reflects what similar items actually sold for. "
            "Active listings tend to run higher, since overpriced items "
            "that haven't sold yet stay visible longer than ones that "
            "sold quickly -- and this dataset isn't split by Loose/CIB."
        ),
    )

    if pricing_basis == "Active eBay listings average":
        active_stats = get_active_listing_stats(confirmed_name, storage_variant)
        if active_stats is None:
            st.warning("No active-listing data for this item/variant -- using sold data instead.")
            base_median, base_min, base_max = get_price_stats(confirmed_name, storage_variant, completeness)
        else:
            base_median, base_min, base_max = active_stats
    else:
        # Sold-data mode still computes the median internally (more robust
        # to outliers than a mean) -- only the displayed label is unified
        # to "Average" so both pricing modes read the same way in the UI.
        base_median, base_min, base_max = get_price_stats(confirmed_name, storage_variant, completeness)

    st.markdown("**Condition issues (optional)**")
    st.caption(
        "Estimated deductions based on typical repair/replacement costs and resale "
        "market behavior -- not derived from this project's sold-listing data, since "
        "that data isn't tagged by defect. Applied multiplicatively, not stacked "
        "additively, to avoid unrealistic combined penalties."
    )
    cond_col1, cond_col2, cond_col3 = st.columns(3)
    broken_screen = cond_col1.checkbox("Screen cracked/broken", key="broken_screen_widget")
    stick_drift = cond_col2.checkbox(DRIFT_LABELS[confirmed_name], key="stick_drift_widget")
    heavy_wear = cond_col3.checkbox("Heavy scratches/wear", key="heavy_wear_widget")
    charger_missing = "Charger / AC adapter" not in included_accessories

    multiplier_table = CONDITION_MULTIPLIERS[confirmed_name]
    condition_multiplier = 1.0
    if broken_screen:
        condition_multiplier *= multiplier_table["screen"]
    if stick_drift:
        condition_multiplier *= multiplier_table["drift"]
    if heavy_wear:
        condition_multiplier *= multiplier_table["wear"]
    if charger_missing:
        condition_multiplier *= multiplier_table["charger"]

    median_price = base_median * condition_multiplier
    min_price = base_min * condition_multiplier
    max_price = base_max * condition_multiplier

    price_col1, price_col2, price_col3 = st.columns(3)
    price_col1.metric("Min", f"${min_price:.2f}")
    price_col2.metric("Average", f"${median_price:.2f}")
    price_col3.metric("Max", f"${max_price:.2f}")
    if condition_multiplier < 1.0:
        st.caption(f"Includes a {(1 - condition_multiplier) * 100:.0f}% condition adjustment vs. base price of ${base_median:.2f}")

    with st.expander("See the individual listings used for this price (click a column to sort)"):
        recent_listings = get_recent_listings(confirmed_name, storage_variant, completeness).copy()
        recent_listings = recent_listings.sort_values("price_usd")
        source_page = recent_listings["source_url"].iloc[0] if not recent_listings.empty else None
        if source_page:
            st.caption(f"Source for all rows below: [{source_page}]({source_page})")
        st.dataframe(
            recent_listings[["date", "price_usd"]],
            hide_index=True,
        )

    with st.expander("See current eBay active listings for this item (real eBay data, snapshot from Aug 28 2026 -- not live, reference only, not used in the price calculation)"):
        matching_active = active_listings_df[
            (active_listings_df["item"] == confirmed_name)
            & (active_listings_df["storage_variant"] == storage_variant)
        ].copy()
        if matching_active.empty:
            st.write("No active-listing snapshot data for this item/variant.")
        else:
            matching_active = matching_active.sort_values("price_usd")
            st.dataframe(
                matching_active[["price_usd", "condition_label", "title"]],
                hide_index=True,
            )

    # --- Step D: urgency presets + editable price ---
    st.subheader("Step 4: Set your price")

    # Reset the suggested price to this item's median whenever the
    # identified item/variant/completeness changes, so an old price from a
    # previous photo doesn't linger.
    pricing_signature = (confirmed_name, storage_variant, completeness, condition_multiplier)
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

    pct_vs_average = (final_price - median_price) / median_price * 100
    st.caption(f"{pct_vs_average:+.1f}% vs. average")

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
        try:
            listing_response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[listing_prompt],
            )
        except Exception:
            st.error("Could not reach Gemini right now -- you may have run out of your daily Gemini API quota. Try again later.")
            st.stop()
        listing_title, _, listing_description = listing_response.text.partition("\n")
        st.session_state["listing_title"] = listing_title.strip()
        st.session_state["listing_description"] = listing_description.strip()

    # --- Step F: final output ---
    if "listing_title" in st.session_state:
        st.subheader("Final listing")
        st.subheader(st.session_state["listing_title"])
        st.write(st.session_state["listing_description"])
        st.metric("Asking price", f"${final_price:.2f}")
