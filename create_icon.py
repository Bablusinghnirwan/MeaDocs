from PIL import Image
import os

# Create build directory if it doesn't exist
os.makedirs('build', exist_ok=True)

# Open the source image
img = Image.open('meadocs.jpg')

# Convert to RGB if necessary
if img.mode != 'RGB':
    img = img.convert('RGB')

# Create icon with multiple sizes
icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save('build/icon.ico', format='ICO', sizes=icon_sizes)

print('✓ Icon created successfully at build/icon.ico')
