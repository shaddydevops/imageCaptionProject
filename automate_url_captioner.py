# automate_url_captioner.py
# pip install transformers pillow requests beautifulsoup4 torch

import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from transformers import AutoProcessor, BlipForConditionalGeneration
import sys

# ----------------------------
# Config
# ----------------------------
DEFAULT_URL = "https://en.wikipedia.org/wiki/IBM"
HEADERS = {"User-Agent": "Mozilla/5.0 (image-captioning-script)"}
MIN_PIXELS = 400  # skip tiny icons (e.g., 20x20)

# ----------------------------
# Load the pretrained processor and model (from Hugging Face Hub)
# ----------------------------
processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# If you have a GPU:
# import torch
# device = "cuda" if torch.cuda.is_available() else "cpu"
# model.to(device)

def is_valid_img_src(src: str) -> bool:
    if not src:
        return False
    s = src.lower()
    # skip obvious non-content images
    if s.endswith(".svg") or "sprite" in s or "icon" in s:
        return False
    if "1x1" in s or "blank" in s:
        return False
    return True

def absolutize_url(page_url: str, img_src: str) -> str:
    # Handle //example.com/img.jpg
    if img_src.startswith("//"):
        return "https:" + img_src
    # Already absolute?
    if img_src.startswith("http://") or img_src.startswith("https://"):
        return img_src
    # Otherwise, build absolute from page URL
    from urllib.parse import urljoin
    return urljoin(page_url, img_src)

def caption_image(pil_image: Image.Image) -> str:
    pil_image = pil_image.convert("RGB")
    # For BLIP, a short prompt helps; omit if you prefer zero-shot
    inputs = processor(images=pil_image, text="the image of", return_tensors="pt")
    # If using GPU: inputs = {k: v.to(device) for k, v in inputs.items()}
    out = model.generate(**inputs, max_new_tokens=50)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption

def main():
    # Allow passing a URL as an argument; else fall back to DEFAULT_URL
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"[INFO] Scraping: {url}")

    # Download page
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    img_elements = soup.find_all("img")

    # Deduplicate images by absolute URL
    seen = set()

    count_total = 0
    count_captioned = 0

    with open("captions.txt", "w", encoding="utf-8") as caption_file:
        for img in img_elements:
            img_src = img.get("src")
            if not is_valid_img_src(img_src):
                continue

            img_url = absolutize_url(url, img_src)
            if img_url in seen:
                continue
            seen.add(img_url)

            try:
                count_total += 1
                # Download the image
                ir = requests.get(img_url, headers=HEADERS, timeout=20)
                ir.raise_for_status()

                # Load as PIL
                raw_image = Image.open(BytesIO(ir.content))
                # Skip very small images
                if raw_image.width * raw_image.height < MIN_PIXELS:
                    continue

                # Generate caption
                caption = caption_image(raw_image)
                caption_file.write(f"{img_url}: {caption}\n")
                count_captioned += 1

                print(f"[OK] {img_url} -> {caption}")

            except Exception as e:
                print(f"[WARN] Error processing image {img_url}: {e}")
                continue

    print(f"\n[DONE] Found: {count_total} imgs | Captioned: {count_captioned}")
    print("Output saved to captions.txt")

if __name__ == "__main__":
    main()
