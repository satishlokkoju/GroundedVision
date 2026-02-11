from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
from IPython.display import display, clear_output, HTML
import ipywidgets as widgets

# Import the annotation manager (make sure the file is in the same directory)
from groundedvision.audit import AnnotationManager, create_audit_session

class ContinuousAnnotator:
    """Manages auto-advancing annotation workflow."""
    
    def __init__(self, manager, qwen_compare_results, PROCESSED_DATA_DIR):
        self.manager = manager
        self.qwen_compare_results = qwen_compare_results
        self.PROCESSED_DATA_DIR = PROCESSED_DATA_DIR
        self.all_samples = list(qwen_compare_results.keys())
        self.main_output = widgets.Output()
        self.update_remaining_samples()
    
    def update_remaining_samples(self):
        """Update list of remaining samples."""
        self.remaining_samples = self.manager.get_unannotated_samples(self.all_samples)
    
    def display_images(self, collage_old, collage_new, old_frame, new_frame):
        """Display comparison images side by side."""
        with self.main_output:
            plt.close('all')
            fig, axes = plt.subplots(1, 2, figsize=(20, 10))
            
            # Old panorama
            try:
                img_old = Image.open(collage_old)
                axes[0].imshow(img_old)
                axes[0].set_title(f'OLD - {old_frame}', fontsize=18, fontweight='bold', pad=20)
                axes[0].axis('off')
            except Exception as e:
                axes[0].text(0.5, 0.5, f'Image not found', ha='center', va='center', fontsize=14)
                axes[0].axis('off')
            
            # New panorama
            try:
                img_new = Image.open(collage_new)
                axes[1].imshow(img_new)
                axes[1].set_title(f'NEW - {new_frame}', fontsize=18, fontweight='bold', pad=20)
                axes[1].axis('off')
            except Exception as e:
                axes[1].text(0.5, 0.5, f'Image not found', ha='center', va='center', fontsize=14)
                axes[1].axis('off')
            
            plt.tight_layout()
            plt.show()
    
    def create_form(self, folder_name, report):
        """Create annotation form."""
        new_frame = report['new_panorama_frame']
        old_frame = report['old_panorama_frame']

        # Build image paths
        collage_new = f"{self.PROCESSED_DATA_DIR}/matched_pairs_json/{folder_name}/new_{new_frame}_aligned_cube_map/collage_border.png"
        collage_old = f"{self.PROCESSED_DATA_DIR}/matched_pairs_json/{folder_name}/old_{old_frame}_aligned_cube_map/collage_border.png"

        # Progress
        completed = len(self.manager.annotations)
        total = len(self.all_samples)
        remaining = len(self.remaining_samples)

        structural_change_detected = report["structural_change_detected"]
        direction_of_progress = report["direction_of_progress"]

        change_description = report["change_description"]

        # Header
        header = widgets.HTML(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="margin: 0;">Structural Change Detected : {structural_change_detected}</h3>
                <h3 style="margin: 0;">direction_of_progress : {direction_of_progress}</h3>
                <p style="margin: 10px 0 0 0; font-size: 14px;">
                    Change Description: {change_description} <br>
                    Progress: {completed}/{total} completed ({remaining} remaining)
                </p>
            </div>
        """)

        # Verdict
        verdict = widgets.RadioButtons(
            options=[
                'True - Model is correct',
                'False - Model is incorrect',
                'Invalid - Frames are not colocated and the registration is incorrect',
                'Bad Quality - frames have motion blur or low quality'
            ],
            description='Verdict:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='600px')
        )

        # Confidence
        confidence = widgets.FloatSlider(
            value=0.8, min=0, max=1, step=0.1,
            description='Confidence:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='400px')
        )

        # Notes
        notes = widgets.Textarea(
            placeholder='Enter your observations here...',
            description='Notes:',
            layout=widgets.Layout(width='100%', height='120px'),
            style={'description_width': '80px'}
        )

        # Buttons
        submit_btn = widgets.Button(
            description='✓ Submit & Next',
            button_style='success',
            layout=widgets.Layout(width='180px', height='45px')
        )
        
        skip_btn = widgets.Button(
            description='⏭ Skip',
            button_style='warning',
            layout=widgets.Layout(width='180px', height='45px')
        )
        
        stop_btn = widgets.Button(
            description='⏸ Stop',
            button_style='danger',
            layout=widgets.Layout(width='180px', height='45px')
        )
        
        feedback = widgets.Output()
        
        # Event handlers
        def on_submit(b):
            verdict_clean = verdict.value.split(' - ')[0]
            metadata = {
                'folder_name': folder_name,
                'new_frame': new_frame,
                'old_frame': old_frame,
                'new_path': collage_new,
                'old_path': collage_old
            }
            
            try:
                self.manager.add_annotation(
                    sample_id=folder_name,
                    verdict=verdict_clean,
                    notes=notes.value,
                    model_output=report,
                    confidence=confidence.value,
                    metadata=metadata,
                    ground_truth=report["structural_change_detected"]
                )
                with feedback:
                    clear_output()
                    print(f"✅ Saved! Moving to next sample...")
                
                self.update_remaining_samples()
                import time
                time.sleep(0.1)
                self.load_next()
                
            except Exception as e:
                with feedback:
                    clear_output()
                    print(f"❌ Error: {e}")
        
        def on_skip(b):
            with feedback:
                clear_output()
                print(f"⏭ Skipped. Loading next...")
            import time
            time.sleep(0.1)
            self.load_next()
        
        def on_stop(b):
            with self.main_output:
                clear_output()
                print("\n" + "="*80)
                print("⏸ SESSION PAUSED")
                print("="*80)
                self.manager.print_summary()
                print("\n💡 To resume: annotator.start()")
        
        submit_btn.on_click(on_submit)
        skip_btn.on_click(on_skip)
        stop_btn.on_click(on_stop)
        
        # Layout
        form = widgets.VBox([
            header,
            verdict,
            confidence,
            notes,
            widgets.HTML("<div style='height: 15px;'></div>"),
            widgets.HBox([submit_btn, skip_btn, stop_btn]),
            feedback
        ], layout=widgets.Layout(
            padding='20px',
            border='2px solid #ddd',
            border_radius='10px',
            background_color='#fafafa'
        ))
        
        return form, (collage_old, collage_new), (old_frame, new_frame)
    
    def load_next(self):
        """Load next sample."""
        self.update_remaining_samples()
        
        if not self.remaining_samples:
            with self.main_output:
                clear_output()
                print("🎉 ALL DONE! GREAT JOB!")
                self.manager.print_summary()
            return
        
        # Get next sample
        sample = self.remaining_samples[0]
        report = self.qwen_compare_results[sample]
        
        # Clear and display
        with self.main_output:
            clear_output(wait=True)
        
        # Create form and get paths
        form, (old_path, new_path), (old_frame, new_frame) = self.create_form(sample, report)
        
        # Display images
        self.display_images(old_path, new_path, old_frame, new_frame)
        
        # Display form
        with self.main_output:
            display(form)
    
    def start(self):
        """Start annotation session."""
        display(self.main_output)
        self.load_next()
