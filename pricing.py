import pandas as pd

df = pd.read_csv("data/raw_sold_listings_all.csv")


def get_recent_listings(model, storage_variant, completeness):
    """
    Given an item's model/variant/completeness, return the last 10 (or fewer)
    matching sold listings, most recent first, as a DataFrame. This is the
    same slice get_price_stats() summarizes -- exposed separately so the app
    can show the individual listings as supporting evidence.
    """
    # 1. keep only the rows that match this exact item/variant/completeness
    matches = df[
        (df['model'] == model)
        & (df['storage_variant'] == storage_variant)
        & (df['completeness'] == completeness)
    ]

    # 2. sort by date, most recent first (string dates sort correctly since they're YYYY-MM-DD)
    matches = matches.sort_values('date', ascending=False)

    # 3. take the last 10 found (or all of them, if fewer than 10 exist)
    return matches.head(10)


def get_price_stats(model, storage_variant, completeness):
    """
    Given an item's model/variant/completeness, return (median, min, max)
    computed from the last 10 (or fewer) matching sold listings.
    """
    recent = get_recent_listings(model, storage_variant, completeness)

    median_price = recent['price_usd'].median()
    min_price = recent['price_usd'].min()
    max_price = recent['price_usd'].max()

    return median_price, min_price, max_price


if __name__ == "__main__":
    # manual test -- try a combo you know exists in the data
    print(get_price_stats("Steam Deck OLED", "512GB", "Loose"))
