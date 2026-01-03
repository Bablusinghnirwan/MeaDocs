# MeaDocs - Electron Build Instructions

## Overview
This document provides complete instructions for building MeaDocs as a Windows desktop application using Electron.

## Prerequisites

### 1. Node.js and npm
- Download and install Node.js (v18 or later) from: https://nodejs.org/
- Verify installation:
  ```powershell
  node --version
  npm --version
  ```

### 2. Python Environment
- Python 3.9+ must be installed
- Your virtual environment (`.venv`) should already have all dependencies installed
- Verify by activating venv and checking:
  ```powershell
  .\.venv\Scripts\activate
  pip list
  ```

## Step-by-Step Build Process

### Step 1: Install Node.js Dependencies
Open PowerShell in the `d:\MeaDocs` directory and run:

```powershell
npm install
```

This will install:
- `electron` - The Electron framework
- `electron-builder` - Tool to package and build the app
- `tree-kill` - Utility to properly terminate Python processes

### Step 2: Test in Development Mode
Before building, test that everything works:

```powershell
npm start
```

This will:
1. Start the Flask backend using your `.venv` Python
2. Open an Electron window loading `http://localhost:5000`
3. You should see your MeaDocs interface

**Troubleshooting Development Mode:**
- If Python doesn't start, check that `.venv\Scripts\python.exe` exists
- If Flask doesn't load, manually test: `.\.venv\Scripts\python.exe app.py`
- Check the Electron console for error messages

### Step 3: Create Application Icon

You need to create a proper Windows icon file:

1. Create a folder: `d:\MeaDocs\build`
2. Convert your `meadocs.jpg` to `icon.ico`:
   - Use an online converter like: https://convertio.co/jpg-ico/
   - Or use a tool like GIMP or Photoshop
   - Recommended sizes: 256x256, 128x128, 64x64, 48x48, 32x32, 16x16
3. Save as: `d:\MeaDocs\build\icon.ico`

**Quick Icon Creation (if you have ImageMagick):**
```powershell
magick convert meadocs.jpg -resize 256x256 build/icon.ico
```

### Step 4: Prepare Python Runtime for Production Build

For a standalone executable, you need to bundle Python with your app.

**Option A: Use Embedded Python (Recommended)**

1. Download Python Embedded Package:
   - Go to: https://www.python.org/downloads/windows/
   - Download "Windows embeddable package (64-bit)" for Python 3.11
   - Example: `python-3.11.7-embed-amd64.zip`

2. Extract to `d:\MeaDocs\python-runtime`:
   ```powershell
   # Create directory
   New-Item -ItemType Directory -Path "python-runtime" -Force
   
   # Extract the downloaded zip to this folder
   Expand-Archive -Path "path\to\python-3.11.7-embed-amd64.zip" -DestinationPath "python-runtime"
   ```

3. Install pip in embedded Python:
   ```powershell
   # Download get-pip.py
   Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
   
   # Install pip
   .\python-runtime\python.exe get-pip.py
   ```

4. Install your requirements:
   ```powershell
   .\python-runtime\python.exe -m pip install -r requirements.txt
   ```

5. Configure embedded Python to find packages:
   - Open `python-runtime\python311._pth` (or similar)
   - Add these lines:
     ```
     .
     .\Lib\site-packages
     import site
     ```

**Option B: Copy Your Virtual Environment (Alternative)**

If Option A is too complex, you can bundle your existing venv:

```powershell
# Copy the entire venv (WARNING: This creates a large bundle)
Copy-Item -Path ".venv" -Destination "python-runtime" -Recurse
```

### Step 5: Build the Windows Executable

Now build the final `.exe`:

```powershell
npm run build:win
```

This command will:
1. Package your entire application
2. Bundle Python runtime, dependencies, and assets
3. Create an installer in the `dist` folder
4. Generate `MeaDocs Setup 1.0.0.exe`

**Build Output:**
- Installer: `dist\MeaDocs Setup 1.0.0.exe`
- Unpacked files: `dist\win-unpacked\` (for testing)

### Step 6: Test the Built Application

**Test the unpacked version first:**
```powershell
.\dist\win-unpacked\MeaDocs.exe
```

**Then test the installer:**
1. Run `dist\MeaDocs Setup 1.0.0.exe`
2. Install to a test location
3. Launch MeaDocs from Start Menu or Desktop shortcut

## Build Customization

### Change App Name or Version
Edit `package.json`:
```json
{
  "name": "meadocs",
  "version": "1.0.0",
  "build": {
    "productName": "MeaDocs"
  }
}
```

### Change Install Options
Edit the `nsis` section in `package.json`:
```json
"nsis": {
  "oneClick": false,  // Set to true for one-click install
  "allowToChangeInstallationDirectory": true,
  "createDesktopShortcut": true,
  "createStartMenuShortcut": true
}
```

### Reduce Build Size
The build might be large due to:
- Python runtime (~50-100 MB)
- AI models (CLIP, Vosk, etc.) (~500 MB - 2 GB)
- Dependencies (PyTorch, etc.) (~500 MB - 1 GB)

**To reduce size:**
1. Use CPU-only versions of PyTorch
2. Use smaller AI models
3. Exclude unnecessary files in `package.json` `files` array

## Troubleshooting

### Build Fails - "Python not found"
- Ensure `python-runtime` folder exists and contains `python.exe`
- Check that all dependencies are installed in the runtime

### App Starts but Shows "Cannot connect"
- The Flask server might not be starting
- Check logs in: `%APPDATA%\MeaDocs\logs\` (if logging is configured)
- Try running the unpacked version to see console output

### Large Installer Size
- This is normal for AI/ML applications
- Typical size: 1-3 GB depending on models
- Consider creating a "lite" version without heavy models

### Icon Not Showing
- Ensure `build/icon.ico` exists
- Rebuild the app after adding the icon
- Windows might cache old icons - restart Explorer

## Distribution

### Sharing Your Application
1. Upload `MeaDocs Setup 1.0.0.exe` to cloud storage or your website
2. Users just download and run the installer
3. No Python or Node.js installation required for end users

### Creating Updates
1. Increment version in `package.json`
2. Rebuild: `npm run build:win`
3. Distribute the new installer

## Advanced: Auto-Updates

To add auto-update functionality:
1. Set up a release server
2. Add `electron-updater` package
3. Configure update URLs in `package.json`
4. See: https://www.electron.build/auto-update

## Complete Command Reference

```powershell
# Install dependencies
npm install

# Run in development mode
npm start

# Build for Windows
npm run build:win

# Build for all platforms (if needed)
npm run build

# Clean build artifacts
Remove-Item -Recurse -Force dist, node_modules
```

## Project Structure After Setup

```
d:\MeaDocs\
├── app.py                          # Flask backend
├── audio_utils.py                  # Audio processing
├── document_utils.py               # Document processing
├── photo_utils.py                  # Photo processing
├── video_utils.py                  # Video processing
├── main.js                         # Electron main process
├── preload.js                      # Electron preload script
├── package.json                    # Node.js configuration
├── requirements.txt                # Python dependencies
├── templates/                      # HTML templates
│   ├── index.html
│   ├── photo_search.html
│   ├── video_search.html
│   ├── document_search.html
│   └── audio_search.html
├── uploads/                        # User uploads
├── vosk-model-en-us-0.22-lgraph/  # Speech recognition model
├── ffmpeg.exe                      # Video processing
├── meadows.jpg                     # App logo
├── build/                          # Build resources
│   └── icon.ico                    # Windows icon
├── python-runtime/                 # Bundled Python (for production)
│   ├── python.exe
│   ├── Lib/
│   └── ...
├── node_modules/                   # Node.js dependencies
├── dist/                           # Build output
│   ├── MeaDocs Setup 1.0.0.exe    # Installer
│   └── win-unpacked/               # Unpacked app
└── .venv/                          # Development Python environment
```

## Support

If you encounter issues:
1. Check the console output when running `npm start`
2. Verify all paths in `main.js` are correct
3. Ensure Python dependencies are installed in `python-runtime`
4. Test the Flask app standalone: `python app.py`

## Next Steps

After successful build:
- [ ] Test on a clean Windows machine without Python/Node.js
- [ ] Create user documentation
- [ ] Set up crash reporting (optional)
- [ ] Implement auto-updates (optional)
- [ ] Code signing for Windows (optional, removes "Unknown Publisher" warning)
