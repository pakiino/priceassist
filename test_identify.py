import os
from google import genai
from google.genai import types

# Reads your key from a local file that is never committed (see .gitignore).
# api_key.example.txt is the committed template; copy it to api_key.txt and
# paste your own key from https://aistudio.google.com/apikey
key_path = os.path.join(os.path.dirname(__file__), "api_key.txt")
with open(key_path, "r", encoding="utf-8") as f:
    api_key = f.read().strip()

if not api_key or api_key == "YOUR_API_KEY_HERE":
    raise SystemExit(
        "No API key found. Open api_key.txt and replace the placeholder "
        "with your own Gemini key from https://aistudio.google.com/apikey"
    )

client = genai.Client(api_key=api_key)

image_path = r"D:\s-l1600.webp"
with open(image_path, "rb") as f:
    image_bytes = f.read()

prompt_text = (
    "This photo shows a resale handheld gaming console. It is one of the following: "
    "Steam Deck, Nintendo Switch Oled TOTK Edition, or Nintendo 3ds XL Hyrule Edition.\n"
    "Reply in exactly this format:\n"
    "Line 1: the exact name of the item from the list above, nothing else.\n"
    "Line 2 onward: a short resale listing description (2-4 sentences) based only on what "
    "is visible in the photo, including any visible wear such as scratches, dents, screen "
    "cracks, or discoloration. Do not claim anything about whether it powers on or "
    "functions correctly — that cannot be determined from a photo."
)

image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/webp")

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[image_part, prompt_text],
)

item_name, _, description = response.text.partition("\n")
item_name = item_name.strip()
description = description.strip()

print("ITEM:", item_name)
print("DESCRIPTION:", description)
