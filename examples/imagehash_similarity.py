from PIL import Image
import imagehash
import requests
import urllib

# Function to calculate phash of an image
def calculate_phash(im, hash_size=8):
    """Calculate perceptual hash of an image."""
    hash_value = imagehash.phash(im, hash_size)
    hash_int = int(str(hash_value), 16)
    return hash_int
        
        
# Function to calculate dhash of an image
def calculate_dhash(im, hash_size=8):
    """Calculate difference hash of an image."""
    hash_value = imagehash.dhash(im, hash_size)
    hash_int = int(str(hash_value), 16)
    return hash_int
    
# Function to compare two images. Bigger hash size is more exact.
def is_same_image(url1, url2, hash_size=8):
    """Compare two images to check if they are the same."""
        
    # Calculate phash and dhash for both images
    im1 = Image.open(urllib.request.urlopen(url1))
    phash1_int = calculate_phash(im1, hash_size)
    dhash1_int = calculate_dhash(im1, hash_size)
        
    im2 = Image.open(urllib.request.urlopen(url2))
    phash2_int = calculate_phash(im2, hash_size)
    dhash2_int = calculate_dhash(im2, hash_size)

    # Compute differences
    phash_diff = bin(phash1_int ^ phash2_int).count('1')
    dhash_diff = bin(dhash1_int ^ dhash2_int).count('1')
                               
    # Print differences
    print(f"{phash_diff}\t{dhash_diff}")
            
    # Determine if images are the same based on calculated differences
    if phash_diff == 0 and dhash_diff < 10:
        return True
    elif phash_diff < 10 and dhash_diff == 0:
        return True
    else:
        return False
    
# Main execution
url1 = 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Viktor-Malmberg.jpg/747px-Viktor-Malmberg.jpg'
url2 = 'https://finna.fi/Cover/Show?source=Solr&id=museovirasto.642DA46A74CEF66FC8015DDA457AA98C&index=0&size=large'

print(url1)    
print(url2)    
result = is_same_image(url1, url2)
print(f"Images are the {'same' if result else 'different'}.")
