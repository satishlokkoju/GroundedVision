"""
Equirectangular Panorama to Cubemap Converter

Converts an equirectangular (360°) panorama image into 6 cube map faces.
NumPy vectorized implementation for efficient processing.

Usage:
    python equirect_to_cubemap.py -i input_panorama.jpg -o output_prefix -r 1024
"""

import numpy as np
from PIL import Image


def create_cube_face_coordinates(edge: int, fov_deg: float = 90.0) -> tuple:
    """
    Create normalized coordinate grids for a cube face.
    
    Args:
        edge: Edge length in pixels
        fov_deg: Field of view in degrees (default 90° for standard cubemap)
        
    Returns:
        Tuple of (a, b) coordinate arrays, each of shape (edge, edge)
        Values are scaled by tan(fov/2) for the specified FOV
    """
    # Create coordinate grids
    i = np.arange(edge)
    j = np.arange(edge)
    ii, jj = np.meshgrid(i, j)
    
    # Normalize to range [-1, 1]
    a = (2.0 * ii) / edge - 1.0
    b = (2.0 * jj) / edge - 1.0
    
    # Scale by FOV (tan of half-angle)
    # For 90° FOV, scale = 1.0 (standard cubemap)
    # For wider FOV, scale > 1.0 (faces overlap)
    # For narrower FOV, scale < 1.0 (faces have gaps)
    fov_scale = np.tan(np.radians(fov_deg / 2.0))
    a = a * fov_scale
    b = b * fov_scale
    
    return a, b


def out_img_to_xyz_vectorized(a: np.ndarray, b: np.ndarray, face: int) -> tuple:
    """
    Convert normalized coordinates on a cube face to 3D direction vectors.
    Vectorized version processing entire face at once.
    
    Args:
        a: Normalized x coordinates array, shape (edge, edge)
        b: Normalized y coordinates array, shape (edge, edge)
        face: Face index (0=back, 1=left, 2=front, 3=right, 4=top, 5=bottom)
    
    Returns:
        Tuple (x, y, z) of 3D direction arrays, each shape (edge, edge)
    """
    ones = np.ones_like(a)
    
    if face == 0:    # back
        x = -ones
        y = -a
        z = -b
    elif face == 1:  # left
        x = a
        y = -ones
        z = -b
    elif face == 2:  # front
        x = ones
        y = a
        z = -b
    elif face == 3:  # right
        x = -a
        y = ones
        z = -b
    elif face == 4:  # top
        x = b
        y = a
        z = ones
    elif face == 5:  # bottom
        x = -b
        y = a
        z = -ones
    else:
        raise ValueError(f"Invalid face index: {face}")
    
    return x, y, z


def xyz_to_equirect_coords(x: np.ndarray, y: np.ndarray, z: np.ndarray, 
                            width: int, height: int) -> tuple:
    """
    Convert 3D direction vectors to equirectangular image coordinates.
    
    Args:
        x, y, z: 3D direction arrays
        width: Equirectangular image width
        height: Equirectangular image height
    
    Returns:
        Tuple (uf, vf) of floating point coordinates in the source image
    """
    # Convert to spherical coordinates
    theta = np.arctan2(y, x)  # longitude: range -pi to pi
    r = np.sqrt(x**2 + y**2)
    phi = np.arctan2(z, r)    # latitude: range -pi/2 to pi/2
    
    # Convert spherical coordinates to equirectangular image coordinates
    # Note: assumes width = 2 * height (standard equirectangular format)
    uf = (theta + np.pi) / np.pi * height
    vf = (np.pi / 2 - phi) / np.pi * height
    
    return uf, vf


def bilinear_interpolate(img: np.ndarray, uf: np.ndarray, vf: np.ndarray) -> np.ndarray:
    """
    Perform bilinear interpolation on the image at floating point coordinates.
    
    Args:
        img: Source image array of shape (H, W, C)
        uf: Horizontal coordinates array
        vf: Vertical coordinates array
    
    Returns:
        Interpolated color values array of shape (*uf.shape, C)
    """
    height, width, channels = img.shape
    
    # Get integer coordinates (floor)
    ui = np.floor(uf).astype(np.int32)
    vi = np.floor(vf).astype(np.int32)
    
    # Clamp to valid range
    ui = np.clip(ui, 0, width - 1)
    vi = np.clip(vi, 0, height - 1)
    u2 = np.clip(ui + 1, 0, width - 1)
    v2 = np.clip(vi + 1, 0, height - 1)
    
    # Fractional parts for interpolation weights
    mu = (uf - ui)[:, :, np.newaxis]  # Add channel dimension
    nu = (vf - vi)[:, :, np.newaxis]
    
    # Sample four corners
    A = img[vi, ui].astype(np.float32)
    B = img[vi, u2].astype(np.float32)
    C = img[v2, ui].astype(np.float32)
    D = img[v2, u2].astype(np.float32)
    
    # Bilinear interpolation
    top = A + (B - A) * mu
    bottom = C + (D - C) * mu
    result = top + (bottom - top) * nu
    
    return np.clip(result, 0, 255).astype(np.uint8)


def generate_cube_face(img_in: np.ndarray, face: int, resolution: int,
                       fov_deg: float = 90.0) -> np.ndarray:
    """
    Generate a single cube map face from the equirectangular image.
    
    Args:
        img_in: Input equirectangular image as numpy array (H, W, C)
        face: Face index (0-5)
        resolution: Output face resolution
        fov_deg: Field of view in degrees (default 90° for standard cubemap)
    
    Returns:
        Face image as numpy array of shape (resolution, resolution, 4)
    """
    height, width = img_in.shape[:2]
    
    # Create coordinate grids with FOV scaling
    a, b = create_cube_face_coordinates(resolution, fov_deg)
    
    # Convert to 3D direction vectors
    x, y, z = out_img_to_xyz_vectorized(a, b, face)
    
    # Convert to equirectangular coordinates
    uf, vf = xyz_to_equirect_coords(x, y, z, width, height)
    
    # Sample colors with bilinear interpolation
    colors = bilinear_interpolate(img_in, uf, vf)
    
    # Create RGBA output
    face_img = np.zeros((resolution, resolution, 4), dtype=np.uint8)
    face_img[:, :, :3] = colors
    face_img[:, :, 3] = 255  # Alpha channel
    
    return face_img


def convert_back(img_in: np.ndarray, resolution: int, fov_deg: float = 120.0) -> list:
    """
    Convert equirectangular panorama to 6 cube map faces.
    Vectorized implementation for efficient processing.
    
    Args:
        img_in: Input equirectangular image as numpy array
        resolution: Output cube face resolution in pixels
        fov_deg: Field of view in degrees (default 90° for standard cubemap)
                 - 90°: Standard cubemap with no overlap
                 - >90°: Faces overlap (useful for blending)
                 - <90°: Faces have gaps (not recommended for complete cubemaps)
    
    Returns:
        List of 6 PIL Images representing the cube faces
    """
    face_names = ['back', 'left', 'front', 'right', 'top', 'bottom']
    output_faces = []
    
    for face in range(6):
        print(f"  Processing face {face} ({face_names[face]})...")
        
        # Generate face using vectorized operations
        face_img = generate_cube_face(img_in, face, resolution, fov_deg)
        
        # Convert to PIL Image
        output_faces.append(Image.fromarray(face_img))
    
    return output_faces


def create_collage(faces: list, resolution: int) -> Image.Image:
    """
    Create a cross-layout collage of the 6 cube faces.
    
    Layout (standard cube cross):
              [top]
        [left][front][right][back]
              [bottom]
    
    Args:
        faces: List of 6 PIL Images (back, left, front, right, top, bottom)
        resolution: Face resolution in pixels
    
    Returns:
        PIL Image of the collage (4*resolution x 3*resolution)
    """
    # Create canvas for cross layout (4 wide x 3 tall)
    collage = Image.new('RGB', (4 * resolution, 3 * resolution), color=(0, 0, 0))
    
    # Face indices: 0=back, 1=left, 2=front, 3=right, 4=top, 5=bottom
    # Cross layout positions:
    #        [4]          <- top at (1, 0)
    #   [1] [2] [3] [0]   <- left, front, right, back at y=1
    #        [5]          <- bottom at (1, 2)
    
    positions = {
        0: (3, 1),  # back
        1: (0, 1),  # left
        2: (1, 1),  # front
        3: (2, 1),  # right
        4: (1, 0),  # top
        5: (1, 2),  # bottom
    }
    
    for face_idx, (col, row) in positions.items():
        x = col * resolution
        y = row * resolution
        collage.paste(faces[face_idx].convert('RGB'), (x, y))
    
    return collage

