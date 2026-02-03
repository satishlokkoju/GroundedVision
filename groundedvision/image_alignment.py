import numpy as np
import cv2
from scipy.spatial.transform import Rotation as R
from pathlib import Path


def rotate_equirectangular(image, pitch, yaw, roll, order='XYZ'):
    """
    Rotate an equirectangular image by the given Euler angles.
    
    This "bakes" the rotation into the image, converting it to standard
    orientation (0, 0, 0). Matches the JavaScript viewer's download behavior.
    
    Args:
        image: Input equirectangular image (numpy array)
        pitch: Pitch angle in degrees (rotation around X axis)
        yaw: Yaw angle in degrees (rotation around Y axis)  
        roll: Roll angle in degrees (rotation around Z axis)
        order: Euler angle order (default 'XYZ' to match THREE.js)
        
    Returns:
        Rotated equirectangular image
    """
    pitch = pitch - 90
    height, width = image.shape[:2]
    
    # Create rotation matrix from Euler angles
    rotation = R.from_euler(order, [pitch, yaw, roll], degrees=True)
    R_matrix = rotation.as_matrix()
    
    # Create pixel coordinate grids
    u = np.arange(width)
    v = np.arange(height)
    u, v = np.meshgrid(u, v)
    
    # Convert destination pixel coordinates to lon/lat
    # lon: -180° to +180° (left to right)
    # lat: +90° to -90° (top to bottom)
    lon = (u.astype(np.float64) / width) * 360.0 - 180.0  # degrees
    lat = 90.0 - (v.astype(np.float64) / height) * 180.0  # degrees
    
    # Convert to radians
    lon_rad = np.deg2rad(lon)
    lat_rad = np.deg2rad(lat)
    
    # Convert to 3D unit sphere coordinates (matching JavaScript)
    # JavaScript: X = sin(phi)*cos(theta), Y = cos(phi), Z = sin(phi)*sin(theta)
    # where phi = 90° - lat (co-latitude), theta = lon
    phi = np.deg2rad(90.0 - lat)  # co-latitude in radians
    
    x = np.sin(phi) * np.cos(lon_rad)  # X = cos(lat) * cos(lon)
    y = np.cos(phi)                     # Y = sin(lat)
    z = np.sin(phi) * np.sin(lon_rad)  # Z = cos(lat) * sin(lon)
    
    xyz = np.stack([x, y, z], axis=-1)  # (height, width, 3)
    
    # Apply INVERSE rotation to find source coordinates
    # For backward mapping: where did this output pixel come from?
    # Using row vectors: xyz @ R.T applies R, xyz @ R applies R^(-1)
    # We want the inverse, so use xyz @ R
    xyz_src = xyz @ R_matrix
    
    # Convert back to spherical coordinates
    x_src, y_src, z_src = xyz_src[..., 0], xyz_src[..., 1], xyz_src[..., 2]
    
    # lat = 90° - acos(y), lon = atan2(z, x)  (matching JavaScript)
    lat_src = 90.0 - np.rad2deg(np.arccos(np.clip(y_src, -1, 1)))
    lon_src = np.rad2deg(np.arctan2(z_src, x_src))
    
    # Convert to source pixel coordinates
    u_src = (lon_src + 180.0) / 360.0 * width
    v_src = (90.0 - lat_src) / 180.0 * height
    
    # Handle wrapping
    u_src = u_src % width
    v_src = np.clip(v_src, 0, height - 1)
    
    # Remap the image
    rotated = cv2.remap(
        image,
        u_src.astype(np.float32),
        v_src.astype(np.float32),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_WRAP
    )
    
    return rotated


def rotate_equirectangular_file(image_path, pitch, yaw, roll, 
                                 output_path=None, suffix='_aligned', order='XYZ'):
    """
    Rotate an equirectangular image file by the given Euler angles.
    
    Reads the image from the given path, applies the rotation, and saves
    the result with a suffix added to the original filename.
    
    Args:
        image_path: Path to input equirectangular image (str or Path)
        pitch: Pitch angle in degrees (rotation around X axis)
        yaw: Yaw angle in degrees (rotation around Y axis)  
        roll: Roll angle in degrees (rotation around Z axis)
        output_path: Optional explicit output path. If None, uses original 
                     path with suffix added before extension.
        suffix: Suffix to add to filename (default '_aligned')
        order: Euler angle order (default 'XYZ' to match THREE.js)
        
    Returns:
        output_path: Path where the rotated image was saved
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Read image
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")
    
    # Rotate
    rotated = rotate_equirectangular(image, pitch, yaw, roll, order=order)
    
    # Determine output path
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}{suffix}{image_path.suffix}"
    else:
        output_path = Path(output_path)
    
    # Save
    cv2.imwrite(str(output_path), rotated)
    print(f"Saved rotated image to: {output_path}")
    
    return output_path


def align_image_files_to_standard(image_path_a, rotation_a, 
                                   image_path_b, rotation_b,
                                   suffix='_aligned', order='XYZ'):
    """
    Align two image files to standard orientation (0, 0, 0).
    
    Args:
        image_path_a: Path to first equirectangular image
        rotation_a: [pitch, yaw, roll] for image A in degrees
        image_path_b: Path to second equirectangular image
        rotation_b: [pitch, yaw, roll] for image B in degrees
        suffix: Suffix to add to output filenames (default '_aligned')
        order: Euler angle order (default 'XYZ')
        
    Returns:
        (output_path_a, output_path_b): Paths to the aligned images
    """
    output_a = rotate_equirectangular_file(
        image_path_a, *rotation_a, suffix=suffix, order=order
    )
    output_b = rotate_equirectangular_file(
        image_path_b, *rotation_b, suffix=suffix, order=order
    )
    return output_a, output_b


def align_images_to_standard(image_a, rotation_a, image_b, rotation_b, order='XYZ'):
    """
    Align both images to standard orientation (0, 0, 0).
    
    Args:
        image_a: First equirectangular image
        rotation_a: [pitch, yaw, roll] for image A in degrees
        image_b: Second equirectangular image
        rotation_b: [pitch, yaw, roll] for image B in degrees
        order: Euler angle order (default 'XYZ')
        
    Returns:
        (aligned_a, aligned_b): Both images rotated to standard orientation
    """
    aligned_a = rotate_equirectangular(image_a, *rotation_a, order=order)
    aligned_b = rotate_equirectangular(image_b, *rotation_b, order=order)
    return aligned_a, aligned_b
