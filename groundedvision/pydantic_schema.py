"""
Pydantic models for generating JSON schemas for construction progress detection.

This module provides two approaches:
1. Static Pydantic models (when triplets are fixed at development time)
"""
from typing import List, Dict, Any, Tuple, Set
from pydantic import BaseModel, Field, model_validator, ConfigDict


# =============================================================================
# APPROACH 1: Static Pydantic Models (Fixed triplets known at design time)
# =============================================================================

class IdentifiedObject(BaseModel):
    """A single identified construction object with class, category, stage, and bbox."""
    model_config = ConfigDict(populate_by_name=True)
    
    class_name: str = Field(..., alias="class", description="Object class name")
    category: str = Field(..., description="Object category")
    stage: str = Field(..., description="Construction stage")
    bbox_2d: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="[ymin, xmin, ymax, xmax] coordinates (0-1000)"
    )


class ConstructionResponse(BaseModel):
    """Response schema for construction progress detection."""
    identified_objects: List[IdentifiedObject] = Field(
        ...,
        description="List of identified construction objects with bounding boxes"
    )


# =============================================================================
# APPROACH 2: Dynamic Pydantic Model Factory (Runtime triplet validation)
# =============================================================================

def create_constrained_response_model(
    triplets: List[Dict[str, str]]
) -> type[BaseModel]:
    """
    Creates a Pydantic model dynamically that validates identified objects
    against a list of valid (class, category, stage) triplets.

    Args:
        triplets: List of dicts with keys: 'class_name', 'category', 'stage'

    Returns:
        A Pydantic BaseModel class that validates responses against the triplets
    
    Example:
        triplets = [
            {"class_name": "Foundation", "category": "Concrete", "stage": "Complete"},
            {"class_name": "Wall", "category": "Brick", "stage": "In Progress"},
        ]
        ResponseModel = create_constrained_response_model(triplets)
        schema = ResponseModel.model_json_schema()
    """
    # Create a set of valid combinations for fast lookup
    valid_combinations: Set[Tuple[str, str, str]] = {
        (t["class_name"], t["category"], t["stage"]) for t in triplets
    }

    class ConstrainedIdentifiedObject(BaseModel):
        """Identified object constrained to valid triplet combinations."""
        model_config = ConfigDict(populate_by_name=True)
        
        class_name: str = Field(..., alias="class")
        category: str
        stage: str
        bbox_2d: List[int] = Field(..., min_length=4, max_length=4)

        @model_validator(mode='after')
        def validate_triplet_combination(self):
            """Ensure the class/category/stage combo is in the valid set."""
            combo = (self.class_name, self.category, self.stage)
            if combo not in valid_combinations:
                raise ValueError(f"Invalid combination: {combo}")
            return self

    class ConstrainedConstructionResponse(BaseModel):
        """Construction response with validated triplet constraints."""
        identified_objects: List[ConstrainedIdentifiedObject] = Field(
            ...,
            description="List of identified construction objects"
        )

    return ConstrainedConstructionResponse


def build_guided_schema_pydantic(triplets: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Generates a JSON schema using Pydantic.
    
    Args:
        triplets: List of valid (class_name, category, stage) combinations
        
    Returns:
        JSON Schema dict
    """
    ResponseModel = create_constrained_response_model(triplets)
    return ResponseModel.model_json_schema()

