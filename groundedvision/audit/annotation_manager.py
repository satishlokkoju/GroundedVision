"""
Annotation Manager for Grounded Vision Models Auditing

This module provides utilities for managing annotations during manual audit
of computer vision model outputs in Jupyter notebooks.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from pathlib import Path
try:
    from IPython.display import display, clear_output
    import ipywidgets as widgets
    HAS_WIDGETS = True
except ImportError:
    HAS_WIDGETS = False


@dataclass
class Annotation:
    """Represents a single annotation entry."""
    sample_id: str
    auditor_alias: str
    timestamp: str
    verdict: str  # e.g., "True", "False", "skip"
    model_output: Optional[Dict[str, Any]] = None
    ground_truth: Optional[Dict[str, Any]] = None
    notes: str = ""
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnnotationManager:
    """
    Manages annotations for Grounded Vision model auditing in Jupyter notebooks.
    
    Usage:
        manager = AnnotationManager()
        manager.start_session()  # Prompts for alias
        
        # For each sample:
        manager.add_annotation(
            sample_id="sample_001",
            verdict="True",
            notes="Model correctly identified all changes"
        )
        
        manager.save()  # Saves after each annotation by default
    """
    
    def __init__(self, auto_save: bool = True):
        """
        Initialize the annotation manager.
        
        Args:
            auto_save: Whether to automatically save after each annotation.
        """
        self.auto_save = auto_save
        self.annotations: List[Annotation] = []
        self.auditor_alias: Optional[str] = None
        self.session_start: Optional[str] = None
        self.annotations_file: Optional[Path] = None  # FIXED: Initialize
        self._widget_output = None

    
    def _load_annotations(self) -> None:
        """Load existing annotations from file."""

        if self.annotations_file is None:
            return
            
        if self.annotations_file.exists():
            try:
                with open(self.annotations_file, 'r') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict):
                    self.annotations = [
                        Annotation(**ann) for ann in data.get('annotations', [])
                    ]
                    print(f"✓ Loaded {len(self.annotations)} existing annotations from {self.annotations_file}")
                elif isinstance(data, list):
                    # Legacy format - list of annotations
                    self.annotations = [Annotation(**ann) for ann in data]
                    print(f"✓ Loaded {len(self.annotations)} existing annotations from {self.annotations_file}")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"⚠ Warning: Could not load annotations: {e}")
                self.annotations = []
        else:
            print(f"ℹ No existing annotations file found. Will create: {self.annotations_file}")
    
    def start_session(self, alias: Optional[str] = None) -> str:
        """
        Start an audit session. Prompts for auditor alias if not provided.
        
        Args:
            alias: Optional auditor alias. If None, will prompt interactively.
            
        Returns:
            The auditor alias being used for this session.
        """
        self.session_start = datetime.now().isoformat()
        
        if alias:
            self.auditor_alias = alias
            self._setup_file_path()
            self._load_annotations()  
        elif HAS_WIDGETS:  
            self._prompt_alias_widget()
        else:
            self._prompt_alias_input()
            self._setup_file_path()
            self._load_annotations()

        return self.auditor_alias
    
    def _setup_file_path(self) -> None:
        """Set up the annotations file path based on auditor alias."""
        if self.auditor_alias:
            annotations_file = f"./annotation_data/annotations_{self.auditor_alias}.json"
            self.annotations_file = Path(annotations_file)
            # Create only the directory containing the file
            self.annotations_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _prompt_alias_widget(self) -> None:
        """Use ipywidgets to prompt for alias."""
        alias_input = widgets.Text(
            value='',
            placeholder='Enter your alias (e.g., john_doe)',
            description='Auditor:',
            style={'description_width': 'initial'}
        )
        
        submit_btn = widgets.Button(
            description='Start Audit Session',
            button_style='primary',
            icon='check'
        )
        
        output = widgets.Output()
        
        def on_submit(b):
            if alias_input.value.strip():
                self.auditor_alias = alias_input.value.strip()
                # Set up file path and load annotations
                self._setup_file_path()
                self._load_annotations()
                
                with output:
                    clear_output()
                    print(f"✓ Audit session started for: {self.auditor_alias}")
                    print(f"  Session start: {self.session_start}")
                    print(f"  Existing annotations: {len(self.annotations)}")
            else:
                with output:
                    clear_output()
                    print("⚠ Please enter a valid alias")
        
        submit_btn.on_click(on_submit)
        
        display(widgets.VBox([
            widgets.HTML("<h3>🔍 Construction Progress Tracking Model Audit Session</h3>"),
            alias_input,
            submit_btn,
            output
        ]))
    
    def _prompt_alias_input(self) -> None:
        """FIXED: Use standard input to prompt for alias (non-widget fallback)."""
        while not self.auditor_alias:
            alias = input("Enter your auditor alias: ").strip()
            if alias:
                self.auditor_alias = alias
                print(f"✓ Audit session started for: {self.auditor_alias}")
                print(f"  Session start: {self.session_start}")
            else:
                print("⚠ Please enter a valid alias")
    
    def add_annotation(
        self,
        sample_id: str,
        verdict: str,
        notes: str = "",
        model_output: Optional[Dict[str, Any]] = None,
        ground_truth: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Annotation:
        """
        Add a new annotation.
        
        Args:
            sample_id: Unique identifier for the sample being annotated.
            verdict: The audit verdict (e.g., "correct", "incorrect", "partial", "skip").
            notes: Any additional notes about the annotation.
            model_output: The model's output for reference.
            ground_truth: Expected/ground truth data if available.
            confidence: Auditor's confidence in their verdict (0-1).
            metadata: Any additional metadata.
            
        Returns:
            The created Annotation object.
        """
        if not self.auditor_alias:
            raise ValueError("No auditor alias set. Call start_session() first.")
        
        annotation = Annotation(
            sample_id=sample_id,
            auditor_alias=self.auditor_alias,
            timestamp=datetime.now().isoformat(),
            verdict=verdict,
            model_output=model_output,
            ground_truth=ground_truth,
            notes=notes,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        self.annotations.append(annotation)
        
        if self.auto_save:
            self.save()
        
        print(f"✓ Annotation added for {sample_id}: {verdict}")
        return annotation
    
    def save(self) -> None:
        """Save annotations to file."""
        if self.annotations_file is None:
            raise ValueError("No annotations file set. Call start_session() first.")
        
        # Ensure directory exists
        self.annotations_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "total_annotations": len(self.annotations)
            },
            "annotations": [asdict(ann) for ann in self.annotations]
        }
        
        with open(self.annotations_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Saved {len(self.annotations)} annotations to {self.annotations_file}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of annotations."""
        if not self.annotations:
            return {"total": 0, "by_verdict": {}, "by_auditor": {}}
        
        by_verdict = {}
        by_auditor = {}
        
        for ann in self.annotations:
            by_verdict[ann.verdict] = by_verdict.get(ann.verdict, 0) + 1
            by_auditor[ann.auditor_alias] = by_auditor.get(ann.auditor_alias, 0) + 1
        
        return {
            "total": len(self.annotations),
            "by_verdict": by_verdict,
            "by_auditor": by_auditor
        }
    
    def get_annotated_sample_ids(self) -> set:
        """Get set of sample IDs that have already been annotated."""
        return {ann.sample_id for ann in self.annotations}
    
    def get_unannotated_samples(self, all_sample_ids: List[str]) -> List[str]:
        """
        Get list of sample IDs that haven't been annotated yet.
        
        Args:
            all_sample_ids: List of all sample IDs to check.
            
        Returns:
            List of sample IDs that haven't been annotated.
        """
        annotated = self.get_annotated_sample_ids()
        return [sid for sid in all_sample_ids if sid not in annotated]
    
    def print_summary(self) -> None:
        """Print a formatted summary of annotations."""
        summary = self.get_summary()
        print("\n" + "="*50)
        print("📊 ANNOTATION SUMMARY")
        print("="*50)
        print(f"Total annotations: {summary['total']}")
        print("\nBy Verdict:")
        for verdict, count in sorted(summary['by_verdict'].items()):
            print(f"  {verdict}: {count}")
        print("\nBy Auditor:")
        for auditor, count in sorted(summary['by_auditor'].items()):
            print(f"  {auditor}: {count}")
        print("="*50 + "\n")


# Convenience function for quick setup
def create_audit_session(alias: Optional[str] = None) -> AnnotationManager:
    """
    Quick setup for an audit session.
    
    Args:
        alias: Optional auditor alias (will prompt if not provided).
        
    Returns:
        Configured AnnotationManager instance.
    """
    manager = AnnotationManager()
    manager.start_session(alias)
    return manager