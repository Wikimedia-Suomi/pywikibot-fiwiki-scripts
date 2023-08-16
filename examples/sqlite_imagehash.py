from PIL import Image
import imagehash
import requests
import urllib
import sqlite3

# Class to handle SQLite operations
class ImageComparisonDB:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Create a table if it doesn't exist."""
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 url1 TEXT NOT NULL,
                 url2 TEXT NOT NULL,
                 hash_size INTEGER NOT NULL,
                 phash_diff INTEGER NOT NULL,
                 dhash_diff INTEGER NOT NULL)
            ''')
        self.conn.commit()

    def store_cached_diff(self, url1, url2, hash_size, phash_diff, dhash_diff):
        """Store the calculated differences between two images."""
        self.c.execute("INSERT INTO urls (url1, url2, hash_size, phash_diff, dhash_diff) VALUES (?, ?, ?, ?, ?)",
                       (url1, url2, hash_size, phash_diff, dhash_diff))
        self.conn.commit()

    def get_cached_diff(self, url1, url2, hash_size=8):
        """Retrieve cached difference of two images if it exists."""
        self.c.execute("SELECT * FROM urls WHERE url1 = ? AND url2 = ? AND hash_size = ? LIMIT 1",
                       (url1, url2, hash_size))
        data = self.c.fetchall()
        if len(data) == 1:
            return data[0]
        elif len(data) > 0:
            print("Error: Multiple rows")
            exit(1)
        return False

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Destructor to close the database connection."""
        self.close()

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


# Function to compare two images
def is_same_image(db, url1, url2, hash_size=8):
    """Compare two images to check if they are the same."""
    
    # Check cache for precomputed differences
    cached_diff = db.get_cached_diff(url1, url2, hash_size)

    if cached_diff:
        print("Using cache")
        phash_diff = cached_diff['phash_diff']
        dhash_diff = cached_diff['dhash_diff']
    else:
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

        # Cache the results
        db.store_cached_diff(url1, url2, hash_size, phash_diff, dhash_diff)

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
db = ImageComparisonDB('musketti2.db')

url1 = 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Viktor-Malmberg.jpg/747px-Viktor-Malmberg.jpg'
url2 = 'https://finna.fi/Cover/Show?source=Solr&id=museovirasto.642DA46A74CEF66FC8015DDA457AA98C&index=0&size=large'
    
result = is_same_image(db, url1, url2)
print(f"Images are the {'same' if result else 'different'}.")

db.close()

