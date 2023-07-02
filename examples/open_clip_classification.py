# This runs a open_clip classification against ajapaik image defined by url
#
### Install
#
# $ python3 -m venv ./venv
# $ source venv/bin/activate
# $ pip install --upgrade pip
# $ pip install open_clip_torch
#
# Running
#
# $ python open_clip_classification.py "https://ajapaik.ee/photo/1158510/Palmse%20mõisa%20park"
 
import open_clip
import torch
import urllib
import sys  
from PIL import Image

# Parse ajapaik id from url
def get_ajapaik_photo_id(url):
    path = urllib.parse.urlparse(url).path
    # split the path into segments
    segments = path.split('/') 
    # return the photo id (which is the second segment in this case)
    return int(segments[2])
    
# Classification code
def classify(model_name, pretrained, device, input_image, classnames):
    model, _, transform = open_clip.create_model_and_transforms(model_name=model_name, pretrained=pretrained )
    model = model.to(device)
    tokenizer = open_clip.get_tokenizer(model_name)
    image = transform(input_image).unsqueeze(0).to(device)
    text = tokenizer(classnames).to(device)
    
    with torch.no_grad(), torch.cuda.amp.autocast():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0].tolist()
        
    for cls_nm, prob in zip(classnames, probs):
        print(f"{cls_nm}: \t {prob:.3%}")
        
        
# get ajapaik photo from command line parameter
if len(sys.argv) > 1:
    url = sys.argv[1]
    print(f"URL: {url}")
    ajapaik_id = get_ajapaik_photo_id(url)
    image_url="https://ajapaik.ee/photo-thumb/" + str(ajapaik_id)
else:
    image_url="https://ajapaik.ee/photo-thumb/1158510/800/palmse-moisa-park/"
    print("No URL provided. Using {image_url} as failback.")

# Available machine vision models
models=[
    { 'modelname':'ViT-B-32', 'pretrained':'laion2b_s34b_b79k'},
    { 'modelname':'coca_ViT-L-14', 'pretrained':'mscoco_finetuned_laion2B-s13B-b90k'},
    { 'modelname':'ViT-g-14', 'pretrained':'laion2b_s34b_b88k'}
]   
    
# Detected classes. Use plain english as classnames. Use separate axis for overlapping classes
        
classnames = [
   [ "no building in the photo", "photo is interior of a building", "photo is exterior of a building" ],
   [ "photo is taken indoors", "photo is taken outdoors" ],
   [ "aerial photo", "photo was taken on raised viewpoint", "photo was taken on ground level" ],
   [ "male", "female", "face", "man", "photo contains children", "no faces in the photo"]
]       
        
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load image
print(image_url)
input_image = Image.open(urllib.request.urlopen(image_url)).convert("RGB")
    
# Do actual classification
for model in models:
    print("\nOpen clip classification (%s / %s)" % (model['modelname'], model['pretrained']) )
    for classrow in classnames:
        classify(model['modelname'], model['pretrained'], device, input_image, classrow)
