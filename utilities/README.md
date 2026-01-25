# 🛠️ GroundedVision Utilities

This folder contains browser-based HTML utilities for working with 360° equirectangular images and videos. These tools are designed for visualization, manipulation, and processing of panoramic media.

---

## 📋 Available Utilities

| Utility | Description |
|---------|-------------|
| [equirectangular.html](#equirectangularhtml) | Generate perspective views from 360° panoramas |
| [viewer360.html](#viewer360html) | Interactive 360° image viewer |
| [viewer360_compare.html](#viewer360_comparehtml) | Compare and align two 360° images |
| [player.html](#playerhtml) | Interactive 360° video player |

---

## 🌐 equirectangular.html

### Non-Overlapping Perspective View Generator

Automatically generates a grid of perspective views covering the entire 360° panorama from an equirectangular image.

### Features

- **Multiple Layout Patterns:**
  - **Equator Band (4×1):** 4 views around the horizon at 0° pitch
  - **Cube Map (6 faces):** Standard cube map with front, back, left, right, up, and down views
  - **Standard Grid (8×4):** 32 views with minimal overlap
  - **Dense Grid (12×6):** 72 views for comprehensive coverage
  - **Custom Grid:** User-defined horizontal and vertical divisions

- **Configurable Parameters:**
  - Field of View (FOV): 60° to 120°
  - View Size: 256px to 1024px

- **Export Options:**
  - Download all generated views as a ZIP file
  - Individual views saved as PNG with descriptive names

### Usage

1. Open `equirectangular.html` in a web browser
2. Upload an equirectangular panorama image
3. Select a layout pattern and adjust parameters
4. Click **"Generate Views"**
5. Download individual views or all as ZIP

### Technical Details

- Uses bilinear interpolation for smooth perspective projection
- Implements per-pixel ray casting from equirectangular to perspective
- Client-side processing using HTML5 Canvas

---

## 🔭 viewer360.html

### Interactive 360° Image Viewer

A Three.js-powered panorama viewer with full rotation control and JSON metadata support.

### Features

- **Interactive Navigation:**
  - Mouse drag to look around
  - Scroll wheel to zoom (adjust FOV)
  - Arrow keys for pan control

- **Orientation Controls (XYZ Euler):**
  - Pitch (X-axis rotation): -180° to 180°
  - Yaw (Y-axis rotation): -180° to 180°
  - Roll (Z-axis rotation): -180° to 180°

- **JSON Metadata Support:**
  - Load image metadata from JSON files
  - Automatically applies rotation from metadata
  - Supports position and rotation data

- **View Controls:**
  - Adjustable Field of View (30° to 120°)
  - Reset orientation and view buttons
  - Toggle control panel with `H` key

### Usage

1. Open `viewer360.html` in a web browser
2. Upload a 360° equirectangular image or load from JSON
3. Use mouse/keyboard to navigate the panorama
4. Adjust orientation using sliders if needed

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` `↓` `←` `→` | Pan view |
| `H` | Toggle control panel |

---

## 🔀 viewer360_compare.html

### 360° Image Comparison Viewer

Compare and align two equirectangular images with independent rotation controls and multiple viewing modes.

### Features

- **Dual Image Support:**
  - Load and configure Image A and Image B independently
  - Individual pitch, yaw, and roll controls for each image
  - Precise input via sliders and numeric fields

- **Comparison Modes:**
  - **Image A:** View only Image A
  - **Image B:** View only Image B
  - **Blend:** Adjustable opacity blend between both images
  - **Split:** Side-by-side split view

- **Alignment Tools:**
  - Lock alignment to navigate while maintaining relative orientation
  - Real-time Lon/Lat display for current view position
  - Export rotated images with applied transformations

- **Export Capabilities:**
  - Download rotated Image A
  - Download rotated Image B
  - Exports full equirectangular images with rotation applied

### Usage

1. Open `viewer360_compare.html` in a web browser
2. Upload Image A and Image B
3. Adjust rotation parameters to align images
4. Switch between comparison modes to verify alignment
5. Lock alignment and navigate freely
6. Export aligned images when satisfied

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Switch to Image A view |
| `2` | Switch to Image B view |
| `3` | Switch to Blend mode |
| `4` | Switch to Split mode |
| `H` | Toggle control panel |

### Technical Details

- Uses XYZ Euler rotation order
- Implements bilinear interpolation for smooth image rotation
- Full equirectangular reprojection for exports
- Chunked processing for responsive UI during export

---

## 🎬 player.html

### Interactive 360° Video Player

A Three.js-powered 360° video player with full playback controls, framerate settings, and orientation adjustments.

### Features

- **Video Playback Controls:**
  - Play/Pause with visual feedback
  - Timeline scrubbing with seek bar
  - Volume control with mute toggle
  - Loop on/off toggle

- **Framerate Control:**
  - Auto (Native) - uses video's native framerate
  - Preset options: 24, 25, 30, 60 fps
  - Limits render updates to target framerate

- **Playback Rate:**
  - Adjustable from 0.25x to 2x speed
  - Smooth slider control

- **Orientation Controls (XYZ Euler):**
  - Pitch (X-axis rotation): -180° to 180°
  - Yaw (Y-axis rotation): -180° to 180°
  - Roll (Z-axis rotation): -180° to 180°

- **View Controls:**
  - Adjustable Field of View (30° to 120°)
  - Fullscreen mode support
  - Mouse drag navigation

- **Performance Stats:**
  - Real-time FPS display
  - Video resolution info
  - Dropped frames counter

### Usage

1. Open `player.html` in a web browser
2. Upload a 360° equirectangular video
3. Use the playback bar to control video playback
4. Drag mouse to look around the 360° scene
5. Adjust orientation and framerate as needed

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `↑` `↓` `←` `→` | Pan view |
| `H` | Toggle control panel |
| `F` | Toggle fullscreen |

### Supported Formats

- MP4 (H.264) - recommended
- WebM (VP8/VP9)
- Other browser-supported video formats

---

## 🚀 Getting Started

### Requirements

- Modern web browser with JavaScript enabled
- No server required - all utilities run entirely client-side

### Running the Utilities

Simply open any HTML file directly in your browser:

```bash
# Using default browser
xdg-open utilities/equirectangular.html    # Linux
open utilities/equirectangular.html         # macOS
start utilities/equirectangular.html        # Windows

# Or drag and drop the HTML file into your browser
```

### Recommended Browsers

- Google Chrome (recommended)
- Mozilla Firefox
- Microsoft Edge
- Safari

---

## 📁 File Structure

```
utilities/
├── README.md                  # This documentation
├── equirectangular.html       # Perspective view generator
├── player.html                # 360° video player
├── viewer360.html             # Single image 360° viewer
└── viewer360_compare.html     # Dual image comparison viewer
```

---

## 💡 Tips & Best Practices

### Image Format Recommendations

- **Input:** JPEG or PNG equirectangular images
- **Aspect Ratio:** 2:1 (e.g., 4096×2048, 8192×4096)
- **Resolution:** Higher resolution provides better quality perspective views

### Performance Considerations

- Large images may take longer to process
- Dense grids generate many views - consider available memory
- Export operations run in chunks to maintain UI responsiveness

### Common Use Cases

1. **Dataset Preparation:** Generate training data from 360° imagery
2. **Image Alignment:** Align multi-capture panoramas using comparison viewer
3. **Quality Inspection:** Verify panorama stitching using rotation controls
4. **View Extraction:** Extract specific perspectives for presentations

---

## 🔧 Dependencies

All utilities use CDN-hosted libraries:

| Library | Version | Usage |
|---------|---------|-------|
| [Three.js](https://threejs.org/) | r128 | 3D rendering for 360° viewers |
| [JSZip](https://stuk.github.io/jszip/) | 3.10.1 | ZIP file generation for exports |

---

## 📝 License

These utilities are part of the GroundedVision project.
