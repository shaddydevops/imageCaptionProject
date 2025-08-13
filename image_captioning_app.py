import gradio as gr
import numpy as np
from PIL import Image
from transformers import AutoProcessor, BlipForConditionalGeneration

# Load processor & model
processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")


def caption_image(input_image: np.ndarray):
    # Convert numpy array to PIL Image and convert to RGB
    raw_image = Image.fromarray(input_image).convert('RGB')
    
    # Prepare inputs (BLIP can take an optional prompt; a short prefix helps)
    inputs = processor(images=raw_image, text="the image of", return_tensors="pt")

    # Generate tokens
    outputs = model.generate(**inputs, max_length=50)

    # Decode tokens to text
    caption = processor.decode(outputs[0], skip_special_tokens=True)
    return caption


iface = gr.Interface(
    fn=caption_image, 
    inputs=gr.Image(), 
    outputs="text",
    title="Image Captioning",
    description="This is a simple web app for generating captions for images using a trained model."
)

iface.launch()