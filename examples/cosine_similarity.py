# Calculate cosine similarity between the two images
#
## Install
# pip install open_clip_torch pillow torch
# 
# Running
# python3 cosine_similarity.py

import urllib
from PIL import Image
import torch
import open_clip

## Fast model
modelname='ViT-B-32'
pretrained='laion2b_s34b_b79k'

## Slower models
#modelname='coca_ViT-L-14'
#pretrained='mscoco_finetuned_laion2b_s13b_b90k'

url1 = 'https://upload.wikimedia.org/wikipedia/commons/d/d4/Artturi-Kannisto.jpg'
url2 = 'https://finna.fi/Cover/Show?source=Solr&id=museovirasto.D85A3BD6A3A0C7ABACB8BD4BAB3B7E05&index=0&size=large'

# Load model
model, _, preprocess = open_clip.create_model_and_transforms(modelname, pretrained=pretrained)
tokenizer = open_clip.get_tokenizer(modelname)

# Load images
im1 = Image.open(urllib.request.urlopen(url1))
im2 = Image.open(urllib.request.urlopen(url2))

with torch.no_grad(), torch.cuda.amp.autocast():
    # Preprocess the images
    image1 = preprocess(im1).unsqueeze(0)
    image2 = preprocess(im2).unsqueeze(0)
    
    # Encode the images
    image1_features = model.encode_image(image1)
    image2_features = model.encode_image(image2)
    
    # Normalize the features
    image1_features /= image1_features.norm(dim=-1, keepdim=True)
    image2_features /= image2_features.norm(dim=-1, keepdim=True)
    
    # Compute the cosine similarity. Value is number between 0 - 1. (0 = different, 1 = similar)
    # Result is model specific
    
    cosine_similarity = (image1_features * image2_features).sum(dim=-1)
    print("Cosine similarity between the two images:", cosine_similarity.item())
