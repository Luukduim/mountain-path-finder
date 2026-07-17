import os
import re
import ast
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter(
    prefix="/api/settings",
    tags=["Settings"]
)

# Navigate from backend/routers/settings.py up to backend/src/config.py
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "config.py")

ALLOWED_SETTINGS = {
    "SMOOTH_PATH",
    "SMOOTH_PATH_LAMBDA",
    "MAIN_SLOPE_PENALTY_ALPHA",
    "WATER_CROSSING_PENALTY"
}

@router.get("/")
def get_settings():
    """Parse config.py and return all uppercase primitive constants."""
    settings = {}
    
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="Config file not found")
        
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    try:
        tree = ast.parse(content)
        
        for node in tree.body:
            # Look for assignments (e.g. VAR_NAME = value)
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in ALLOWED_SETTINGS:
                    if isinstance(node.value, ast.Constant):
                        val = node.value.value
                        if isinstance(val, (int, float, bool, str)):
                            settings[target.id] = val
                    # Fallback for older python versions where Num/Str/NameConstant are used
                    elif hasattr(ast, 'Num') and isinstance(node.value, ast.Num):
                        settings[target.id] = node.value.n
                    elif hasattr(ast, 'Str') and isinstance(node.value, ast.Str):
                        settings[target.id] = node.value.s
                    elif hasattr(ast, 'NameConstant') and isinstance(node.value, ast.NameConstant):
                        settings[target.id] = node.value.value
    except Exception as e:
        print(f"Error parsing config.py: {e}")
        
    return settings

@router.put("/")
def update_settings(updates: Dict[str, Any]):
    """Update config.py with new values."""
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="Config file not found")
        
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    changes_made = False
    
    for key, value in updates.items():
        if key not in ALLOWED_SETTINGS:
            continue
            
        if isinstance(value, bool):
            val_str = "True" if value else "False"
        elif isinstance(value, str):
            val_str = f'"{value}"'
        else:
            val_str = str(value)
            
        pattern = rf"^({key})\s*=\s*.*$"
        replacement = rf"\1 = {val_str}"
        
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            content = new_content
            changes_made = True
            
    if changes_made:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": "Settings updated. Server restarting..."}
    else:
        return {"status": "success", "message": "No changes were made."}
