# Example image classification to predefined classes using Lavis and open_lcip

import open_clip
import torch
import pywikibot
import urllib
from PIL import Image
from lavis.models import load_model_and_preprocess

# Test files
filenames=[
    'Turku Castle 1.jpg', 
    'Cuby & Blizzards Muweum Grolloo - 06.JPG', 
    'USS Sumner (DD-333) underway, circa in the middle or later 1920s (NH 70952).jpg',
    'Hastings Half Marathon 2015 FNK 2961 (16740907029).jpg'
]
filename=filenames[0]

# Class names
cls_names = ["interior", "exterior", "aerial photo", "raised viewpoint", "ground level", "male", "female", "face", "man", "woman"]

site = pywikibot.Site('commons', 'commons')  # Select your wiki e.g., English Wikipedia
imagepage = pywikibot.FilePage(site, filename)  # Replace 'Image_Title.jpg' with your image's title
file_url=imagepage.get_file_url(url_width=500)
file_text=imagepage.text
print(file_url)

raw_image = Image.open(urllib.request.urlopen(file_url)).convert("RGB")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

### Clip classification ###
# https://github.com/salesforce/LAVIS/blob/4a85b17846ee62f09c40f37cc955dd33c2abec68/examples/clip_zero_shot_classification.ipynb

model, vis_processors, txt_processors = load_model_and_preprocess("clip_feature_extractor", model_type="ViT-B-16", is_eval=True, device=device)

# Extract image embedding and class name embeddings
cls_names = [txt_processors["eval"](cls_nm) for cls_nm in cls_names]
image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)

sample = {"image": image, "text_input": cls_names}
clip_features = model.extract_features(sample)

image_features = clip_features.image_embeds_proj
text_features = clip_features.text_embeds_proj

# Matching image embeddings with each class name embeddings  
sims = (image_features @ text_features.t())[0] / 0.01
probs = torch.nn.Softmax(dim=0)(sims).tolist()

print("\nClip classification (clip_feature_extractor / ViT-B-16)")
for cls_nm, prob in zip(cls_names, probs):
    print(f"{cls_nm}: \t {prob:.3%}")

### albef image classification ###
# https://github.com/salesforce/LAVIS/blob/4a85b17846ee62f09c40f37cc955dd33c2abec68/examples/albef_zero_shot_classification.ipynb

model, vis_processors, txt_processors = load_model_and_preprocess("albef_feature_extractor", model_type="base", is_eval=True, device=device)
cls_names = [txt_processors["eval"](cls_nm) for cls_nm in cls_names]
image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
sample = {"image": image, "text_input": cls_names}
image_features = model.extract_features(sample, mode="image").image_embeds_proj[:, 0]
text_features = model.extract_features(sample, mode="text").text_embeds_proj[:, 0]
sims = (image_features @ text_features.t())[0] / model.temp
probs = torch.nn.Softmax(dim=0)(sims).tolist()

print("\nAlbef classification (albef_feature_extractor / base)")
for cls_nm, prob in zip(cls_names, probs):
    print(f"{cls_nm}: \t {prob:.3%}")

### blip image classification ###
# https://github.com/salesforce/LAVIS/blob/4a85b17846ee62f09c40f37cc955dd33c2abec68/examples/blip_zero_shot_classification.ipynb

#model, vis_processors, _ = load_model_and_preprocess("blip2_feature_extractor", model_type="base", is_eval=True, device=device)
model, vis_processors, txt_processors = load_model_and_preprocess(name="blip2_feature_extractor", model_type="pretrain", is_eval=True, device=device)
from lavis.processors.blip_processors import BlipCaptionProcessor

text_processor = BlipCaptionProcessor(prompt="A picture of ")
cls_prompt = [text_processor(cls_nm) for cls_nm in cls_names]
image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
sample = {"image": image, "text_input": cls_names}

image_features = model.extract_features(sample, mode="image").image_embeds_proj[:, 0]
text_features = model.extract_features(sample, mode="text").text_embeds_proj[:, 0]

sims = (image_features @ text_features.t())[0] / model.temp
probs = torch.nn.Softmax(dim=0)(sims).tolist()

print("\nBlip2 classification (blip2_feature_extractor / pretrain)")
for cls_nm, prob in zip(cls_names, probs):
    print(f"{cls_nm}: \t {prob:.3%}")

### OpenClip : coca_ViT-L-14 ####

model, _, transform = open_clip.create_model_and_transforms(model_name="coca_ViT-L-14", pretrained="mscoco_finetuned_laion2B-s13B-b90k" )
model = model.to(device)
tokenizer = open_clip.get_tokenizer('coca_ViT-L-14')
image = transform(raw_image).unsqueeze(0).to(device)
text = tokenizer(cls_names).to(device)

with torch.no_grad(), torch.cuda.amp.autocast():
    image_features = model.encode_image(image)
    text_features = model.encode_text(text)
    image_features /= image_features.norm(dim=-1, keepdim=True)
    text_features /= text_features.norm(dim=-1, keepdim=True)
    probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0].tolist()

print("\nOpen clip classification (coca_ViT-L-14 / mscoco_finetuned_laion2B-s13B-b90k)")
for cls_nm, prob in zip(cls_names, probs):
    print(f"{cls_nm}: \t {prob:.3%}")

### OpenClip : ViT-B-32 ####

model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
model = model.to(device)
tokenizer = open_clip.get_tokenizer('ViT-B-32')

image = transform(raw_image).unsqueeze(0).to(device)
text = tokenizer(cls_names).to(device)

with torch.no_grad(), torch.cuda.amp.autocast():
    image_features = model.encode_image(image)
    text_features = model.encode_text(text)
    image_features /= image_features.norm(dim=-1, keepdim=True)
    text_features /= text_features.norm(dim=-1, keepdim=True)
    probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0].tolist()

print("\nOpen clip classification (ViT-B-32 / laion2b_s34b_b79k)")
for cls_nm, prob in zip(cls_names, probs):
    print(f"{cls_nm}: \t {prob:.3%}")

### OpenClip : ViT-G/14 ####

model, _, preprocess = open_clip.create_model_and_transforms('ViT-g-14', pretrained='laion2b_s34b_b88k')
model = model.to(device)
tokenizer = open_clip.get_tokenizer('ViT-g-14')

image = transform(raw_image).unsqueeze(0).to(device)
text = tokenizer(cls_names).to(device)

with torch.no_grad(), torch.cuda.amp.autocast():
    image_features = model.encode_image(image)
    text_features = model.encode_text(text)
    image_features /= image_features.norm(dim=-1, keepdim=True)
    text_features /= text_features.norm(dim=-1, keepdim=True)
    probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0].tolist()

print("\nOpen clip classification (ViT-g-14 / laion2b_s34b_b88k)")
for cls_nm, prob in zip(cls_names, probs):
    print(f"{cls_nm}: \t {prob:.3%}")
