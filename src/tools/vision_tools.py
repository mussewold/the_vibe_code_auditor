import base64
from pathlib import Path
from typing import List, Dict, Any

from src.state import Evidence

def extract_images_from_pdf(path: str) -> List[dict]:
    """
    Extracts images from a given PDF file and returns them as a list of dicts
    containing base64 encoded image strings and metadata.
    """
    import fitz  # PyMuPDF
    
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
    doc = fitz.open(pdf_path)
    extracted_images = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Convert to base64 for LLM API ingestion
            base64_img = base64.b64encode(image_bytes).decode('utf-8')
            
            extracted_images.append({
                "page": page_num + 1,
                "index": img_index,
                "ext": image_ext,
                "data": base64_img
            })
            
    return extracted_images


def analyze_diagram_with_llm(image_b64: str, mime_type: str) -> Dict[str, Any]:
    """
    Send an image to a multimodal LLM (OpenAI gpt-4o) to classify if it's a 
    StateGraph architecture diagram or a generic flowchart.
    """
    from openai import OpenAI
    import json
    import os
    
    # Needs OPENAI_API_KEY in the environment
    # Check OPENAI_API_KEY early to avoid crashing LangGraph
    if not os.environ.get("OPENAI_API_KEY"):
        return {
            "is_stategraph": False,
            "rationale": "Vision API evaluation skipped: OPENAI_API_KEY environment variable is missing."
        }

    client = OpenAI()
    
    prompt = (
        "You are an expert software architect evaluating technical diagrams. "
        "Analyze this image carefully.\n\n"
        "Question: Is this an accurate LangGraph State Machine diagram that explicitly "
        "shows parallel fan-out and fan-in execution paths, or is it just a generic "
        "sequential flowchart / block diagram?\n\n"
        "Return a JSON object with exactly two keys:\n"
        "- 'is_stategraph' (boolean): True if it clearly depicts parallel LangGraph architecture, False otherwise.\n"
        "- 'rationale' (string): A short explanation of your decision."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{mime_type};base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content
        return json.loads(result_text)
        
    except Exception as e:
        return {
            "is_stategraph": False,
            "rationale": f"Vision API evaluation failed: {str(e)}"
        }
