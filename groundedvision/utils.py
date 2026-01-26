import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
import math
import os
from pathlib import Path
from loguru import logger


class EquirectangularConverter:
    """Convert equirectangular panoramas to perspective views"""
    
    def __init__(self, equirect_path):
        """
        Initialize converter with an equirectangular image
        
        Args:
            equirect_path: Path to equirectangular image file
        """
        self.equirect = Image.open(equirect_path)
        self.equirect_array = np.array(self.equirect, dtype=np.float32)  # float for interpolation
        self.width = self.equirect.width
        self.height = self.equirect.height
       
    def render_perspective(self, yaw, pitch, fov, output_width, output_height):
        """Vectorized perspective rendering - 100x+ faster"""
        # Convert to radians
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        fov_rad = np.radians(fov)
        
        # Focal length
        f = output_width / (2 * np.tan(fov_rad / 2))
        
        # Create meshgrid of pixel coordinates (vectorized)
        x = np.arange(output_width)
        y = np.arange(output_height)
        x_grid, y_grid = np.meshgrid(x, y)
        
        # Screen to normalized coordinates
        nx = (x_grid - output_width / 2) / f
        ny = (y_grid - output_height / 2) / f
        
        # Ray directions (vectorized)
        dx = nx
        dy = -ny
        dz = np.ones_like(nx)
        
        # Normalize rays
        length = np.sqrt(dx**2 + dy**2 + dz**2)
        dx /= length
        dy /= length
        dz /= length
        
        # Pre-compute trig values (compute once, not per-pixel)
        cos_pitch, sin_pitch = np.cos(pitch_rad), np.sin(pitch_rad)
        cos_yaw, sin_yaw = np.cos(yaw_rad), np.sin(yaw_rad)
        
        # Apply pitch rotation (around x-axis)
        dy2 = dy * cos_pitch - dz * sin_pitch
        dz2 = dy * sin_pitch + dz * cos_pitch
        
        # Apply yaw rotation (around y-axis)
        dx3 = dx * cos_yaw + dz2 * sin_yaw
        dz3 = -dx * sin_yaw + dz2 * cos_yaw
        
        # Convert to spherical coordinates
        theta = np.arctan2(dx3, dz3)
        phi = np.arcsin(np.clip(dy2, -1, 1))
        
        # Map to equirectangular coordinates
        src_x = ((theta + np.pi) / (2 * np.pi)) * self.width
        src_y = ((np.pi / 2 - phi) / np.pi) * self.height
        
        # Handle wraparound for x
        src_x = src_x % self.width
        src_y = np.clip(src_y, 0, self.height - 1)
        
        # Use scipy's map_coordinates for fast bilinear interpolation
        output = np.zeros((output_height, output_width, 3), dtype=np.uint8)
        for c in range(3):  # RGB channels
            output[:, :, c] = map_coordinates(
                self.equirect_array[:, :, c],
                [src_y, src_x],
                order=1,  # bilinear
                mode='wrap'  # handle horizontal wraparound
            )
        
        return Image.fromarray(output)
 
    def render_perspective_pixel(self, yaw, pitch, fov, output_width, output_height):
        """
        Render a perspective view from the equirectangular image
        
        Args:
            yaw: Horizontal rotation in degrees (-180 to 180)
            pitch: Vertical rotation in degrees (-90 to 90)
            fov: Field of view in degrees (30 to 120)
            output_width: Width of output image in pixels
            output_height: Height of output image in pixels
            
        Returns:
            PIL Image of the perspective view
        """
        # Convert angles to radians
        yaw_rad = math.radians(yaw)
        pitch_rad = math.radians(pitch)
        fov_rad = math.radians(fov)
        
        # Calculate focal length
        f = output_width / (2 * math.tan(fov_rad / 2))
        
        # Create output array
        output = np.zeros((output_height, output_width, 3), dtype=np.uint8)
        
        for y in range(output_height):
            for x in range(output_width):
                # Screen to normalized coordinates
                nx = (x - output_width / 2) / f
                ny = (y - output_height / 2) / f
                
                # Ray direction
                dx = nx
                dy = -ny
                dz = 1
                
                # Normalize
                length = math.sqrt(dx*dx + dy*dy + dz*dz)
                dx /= length
                dy /= length
                dz /= length
                
                # Apply pitch rotation (around x-axis)
                dy2 = dy * math.cos(pitch_rad) - dz * math.sin(pitch_rad)
                dz2 = dy * math.sin(pitch_rad) + dz * math.cos(pitch_rad)
                
                # Apply yaw rotation (around y-axis)
                dx3 = dx * math.cos(yaw_rad) + dz2 * math.sin(yaw_rad)
                dz3 = -dx * math.sin(yaw_rad) + dz2 * math.cos(yaw_rad)
                
                # Convert to spherical coordinates
                theta = math.atan2(dx3, dz3)
                phi = math.asin(max(-1, min(1, dy2)))  # Clamp to avoid numerical errors
                
                # Map to equirectangular coordinates
                src_x = ((theta + math.pi) / (2 * math.pi)) * self.width
                src_y = ((math.pi / 2 - phi) / math.pi) * self.height
                
                # Bilinear interpolation
                x0 = int(src_x) % self.width
                x1 = (x0 + 1) % self.width
                y0 = max(0, min(self.height - 1, int(src_y)))
                y1 = max(0, min(self.height - 1, y0 + 1))
                
                fx = src_x - int(src_x)
                fy = src_y - int(src_y)
                
                # Get surrounding pixels
                p00 = self.equirect_array[y0, x0]
                p10 = self.equirect_array[y0, x1]
                p01 = self.equirect_array[y1, x0]
                p11 = self.equirect_array[y1, x1]
                
                # Interpolate
                v0 = p00 * (1 - fx) + p10 * fx
                v1 = p01 * (1 - fx) + p11 * fx
                output[y, x] = v0 * (1 - fy) + v1 * fy
        
        return Image.fromarray(output)
    
    def generate_cube_map(self, face_size=512, output_dir='cube_faces'):
        """
        Generate 6 cube map faces
        
        Args:
            face_size: Size of each cube face in pixels
            output_dir: Directory to save the faces
            
        Returns:
            Dictionary of face names to PIL Images
        """
        faces = {
            'front': (0, 0),
            'right': (90, 0),
            'back': (180, 0),
            'left': (-90, 0),
            'down': (0, 90),
            'up': (0, -90)
        }
        
        results = {}
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for name, (yaw, pitch) in faces.items():
            img = self.render_perspective(yaw, pitch, 90, face_size, face_size)
            results[name] = img
            img.save(f'{output_dir}/{name}.png')
            logger.info(f'Generated {name} face')
        
        return results
    
    def generate_grid(self, h_count=8, v_count=4, fov=90, view_size=512, output_dir='grid_views'):
        """
        Generate a grid of non-overlapping perspective views
        
        Args:
            h_count: Number of horizontal divisions
            v_count: Number of vertical divisions
            fov: Field of view for each view
            view_size: Size of each view in pixels
            output_dir: Directory to save views
            
        Returns:
            List of tuples (yaw, pitch, image)
        """
        results = []
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        yaw_step = 360 / h_count
        pitch_range = 180
        pitch_step = pitch_range / (v_count + 1)
        
        view_num = 1
        for v in range(v_count):
            pitch = 90 - pitch_step * (v + 1)
            
            for h in range(h_count):
                yaw = h * yaw_step
                
                img = self.render_perspective(yaw, pitch, fov, view_size, view_size)
                results.append((yaw, pitch, img))
                
                filename = f'{output_dir}/view_{view_num:03d}_y{int(yaw):03d}_p{int(pitch):+03d}.png'
                img.save(filename)
                logger.info(f'Generated view {view_num}/{h_count * v_count}: yaw={yaw:.0f}°, pitch={pitch:.0f}°')
                view_num += 1
        
        return results
    
    def generate_equator_band(self, count=4, fov=90, view_size=512, output_dir='equator_views'):
        """
        Generate views around the horizon
        
        Args:
            count: Number of views around the equator
            fov: Field of view for each view
            view_size: Size of each view in pixels
            output_dir: Directory to save views
            
        Returns:
            List of tuples (yaw, image)
        """
        results = []
        # create output directory if it does not exist recursively
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        yaw_step = 360 / count
        
        for i in range(count):
            yaw = i * yaw_step
            img = self.render_perspective(yaw, 0, fov, view_size, view_size)
            results.append((yaw, img))
            
            filename = f'{output_dir}/equator_{i+1:02d}_y{int(yaw):03d}.png'
            img.save(filename)
            logger.info(f'Generated equator view {i+1}/{count}: yaw={yaw:.0f}°')
        
        return results
