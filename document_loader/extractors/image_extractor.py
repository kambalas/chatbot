from __future__ import annotations
from pathlib import Path


def extract_text(path: Path) -> str:
    try:
        from PIL import Image
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch
    except ImportError:
        return ""

    try:
        image = Image.open(path).convert("RGB")

        processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
        model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )

        inputs = processor(image, return_tensors="pt")
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=50)

        caption = processor.decode(output[0], skip_special_tokens=True)
        return caption.strip()
    except Exception:
        return ""
