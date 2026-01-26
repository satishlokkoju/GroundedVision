import os
from groundedvision.utils import EquirectangularConverter
from loguru import logger

def projective_view(image_path: str, output_dir: str):

    # Get File name and extension
    file_name = os.path.basename(image_path)
    file_name = os.path.splitext(file_name)[0]

    # Initialize converter with your equirectangular image
    converter = EquirectangularConverter(image_path)
    
    # Option 1: Generate cube map (6 faces)
    logger.info('\n=== Generating Cube Map ===')
    cube_faces = converter.generate_cube_map(face_size=1024, output_dir=f'{output_dir}/{file_name}_cube_map')
    
    '''

    # Option 2: Generate standard grid (8x4 = 32 views)
    logger.info('\n=== Generating Standard Grid ===')
    grid_views = converter.generate_grid(
        h_count=8, 
        v_count=4, 
        fov=90, 
        view_size=512, 
        output_dir=f'{output_dir}/{file_name}_grid_8x4'
    )
    
    # Option 3: Generate dense grid (12x6 = 72 views)
    logger.info('\n=== Generating Dense Grid ===')
    dense_views = converter.generate_grid(
        h_count=12, 
        v_count=6, 
        fov=75, 
        view_size=512, 
        output_dir=f'{output_dir}/{file_name}_grid_12x6'
    )
    
    # Option 4: Generate equator band (4 views at horizon)
    logger.info('\n=== Generating Equator Band ===')
    equator_views = converter.generate_equator_band(
        count=4, 
        fov=90, 
        view_size=512, 
        output_dir=f'{output_dir}/{file_name}_equator'
    )
    
    # Option 5: Generate single custom view
    logger.info('\n=== Generating Custom View ===')
    custom_view = converter.render_perspective(
        yaw=45,      # Look 45° to the right
        pitch=30,    # Look 30° up
        fov=90,      # 90° field of view
        output_width=1920,
        output_height=1080
    )
    custom_view.save(f'{output_dir}/{file_name}_custom_view.png')
    '''
    
    logger.info('\n=== Done! ===')