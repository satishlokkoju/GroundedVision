# Construction Progress Analyzer Module
"""
Simplified VLM-based construction progress analyzer.
Supports class-specific analysis for focused and efficient inference.
"""

import os
import json
import base64
import mimetypes
from typing import List, Dict, Any, Optional
from openai import OpenAI

from .taxonomy import get_triplets, get_markdown_table, MEP_CLASSES, STRUCTURAL_CLASSES, FINISHES_CLASSES
from groundedvision.pydantic_schema import build_guided_schema_pydantic


def encode_image(image_path: str) -> str:
    """Encode local image to base64 data URI."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")
    
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
    
    with open(image_path, "rb") as image_file:
        base64_encoded = base64.b64encode(image_file.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{base64_encoded}"


def analyze_image(
    image_input: str,
    classes: Optional[List[str]] = None,
    model_name: str = "Qwen/Qwen3-VL-Instruct",
    base_url: str = "http://localhost:8000/v1",
    temperature: float = 0.1,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Analyze a construction site image using VLM.
    
    Args:
        image_input: URL or local path to image
        classes: Optional list of classes to focus on (e.g., ["Mechanical", "Electrical"]).
                 If None, uses full taxonomy.
        model_name: VLM model name
        base_url: API endpoint
        temperature: Sampling temperature
        verbose: Print progress and results
    
    Returns:
        Parsed analysis result dict or None on error
    """
    # Get filtered triplets and schema
    triplets = get_triplets(classes)
    schema = build_guided_schema_pydantic(triplets)
    taxonomy_table = get_markdown_table(classes)
    
    # Prepare image
    if image_input.startswith("http://") or image_input.startswith("https://"):
        final_image_url = image_input
    else:
        if verbose:
            print(f"Encoding local image: {image_input}...")
        final_image_url = encode_image(image_input)
    
    # Setup client
    client = OpenAI(api_key="EMPTY", base_url=base_url)
    
    # Detailed prompts with explicit output format instructions
    class_hint = f"\nFocus primarily on: {', '.join(classes)}." if classes else ""
    
    system_prompt = f"""You are an expert Construction Progress Tracker.
Your job is to identify construction elements in an image and classify them according to a project taxonomy.

You MUST respond with a JSON object using EXACTLY this structure:
{{
  "thought_process": "<your step-by-step reasoning about what you see>",
  "identified_objects": [
    {{
      "class": "<Class name from taxonomy>",
      "category": "<Category from taxonomy>",
      "stage": "<Stage from taxonomy>",
      "bbox_2d": [ymin, xmin, ymax, xmax]
    }}
  ]
}}

CRITICAL REQUIREMENTS:
1. Use EXACTLY these field names: "thought_process", "identified_objects", "class", "category", "stage", "bbox_2d"
2. bbox_2d must be an array of 4 integers: [ymin, xmin, ymax, xmax] in pixel coordinates
3. Select Class, Category, and Stage values ONLY from the provided taxonomy
4. Include ALL visible construction elements{class_hint}"""

    user_prompt = f"""Analyze this construction site image.

AVAILABLE TAXONOMY (Class | Category | Stage):
{taxonomy_table}

Instructions:
1. First, describe your reasoning in "thought_process" - what materials, textures, and construction elements do you observe?
2. Then, list every identified element in "identified_objects" with:
   - "class": The main class from the taxonomy (e.g., "Concrete", "Structural Steel", "Mechanical")
   - "category": The specific category (e.g., "Structural Beams - Steel", "Mechanical Duct")
   - "stage": The construction stage (e.g., "Beams Installed", "Duct Installed")
   - "bbox_2d": Bounding box as [ymin, xmin, ymax, xmax] integers

Remember: Use the EXACT field names specified. Do NOT use alternative names like "bounding_box" or "elements"."""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": final_image_url}}
            ]
        }
    ]
    
    if verbose:
        print(f"Sending request to {model_name}...")
        if classes:
            print(f"Filtering to classes: {classes}")
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "analysis_results",
                    "schema": schema
                },
            },
        )
        
        result_content = response.choices[0].message.content
        parsed_result = json.loads(result_content)
        
        # Normalize result - handle both list and dict responses
        if isinstance(parsed_result, list):
            # Model returned list directly, wrap it
            parsed_result = {"thought_process": "", "identified_objects": parsed_result}
        
        # Handle nested structure variations
        identified_objects = parsed_result.get("identified_objects", [])
        if not identified_objects and isinstance(parsed_result, dict):
            # Maybe the result is the objects directly keyed differently
            for key in ["objects", "elements", "items"]:
                if key in parsed_result:
                    identified_objects = parsed_result[key]
                    break
        
        if verbose:
            print("\n=== Analysis Results ===")
            thought = parsed_result.get('thought_process', '') if isinstance(parsed_result, dict) else ''
            if thought:
                print(f"Thinking: {thought}\n")
            print(f"{'CLASS':<15} | {'CATEGORY':<30} | {'STAGE':<25} | {'BBOX'}")
            print("-" * 90)
            for item in identified_objects:
                cls = item.get('class', 'N/A')
                cat = item.get('category', 'N/A')
                stg = item.get('stage', 'N/A')
                bbox = item.get('bbox_2d', [])
                print(f"{cls:<15} | {cat:<30} | {stg:<25} | {bbox}")
        
        return parsed_result
    
    except Exception as e:
        print(f"Error during inference: {e}")
        return None


def analyze_mep(image_input: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Analyze MEP systems (Mechanical, Electrical, Plumbing, Fire Protection)."""
    return analyze_image(image_input, classes=MEP_CLASSES, **kwargs)


def analyze_structural(image_input: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Analyze structural elements (Concrete, Steel, Wood)."""
    return analyze_image(image_input, classes=STRUCTURAL_CLASSES, **kwargs)


def analyze_finishes(image_input: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Analyze finishes (Walls, Ceiling, Flooring, Doors)."""
    return analyze_image(image_input, classes=FINISHES_CLASSES, **kwargs)


def analyze_all_domains(
    image_input: str,
    domains: List[str] = ["mep", "structural", "finishes"],
    **kwargs
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Run multiple focused analyses on the same image.
    
    Args:
        image_input: Image URL or path
        domains: List of domains to analyze: "mep", "structural", "finishes"
    
    Returns:
        Dict mapping domain names to their results
    """
    results = {}
    
    domain_funcs = {
        "mep": analyze_mep,
        "structural": analyze_structural,
        "finishes": analyze_finishes,
    }
    
    for domain in domains:
        if domain in domain_funcs:
            print(f"\n{'='*20} Analyzing {domain.upper()} {'='*20}")
            results[domain] = domain_funcs[domain](image_input, **kwargs)
    
    return results
