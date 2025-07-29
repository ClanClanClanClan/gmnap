#!/usr/bin/env python3
"""
Fix syntax error in pipeline - escaped characters need to be unescaped
"""

from pathlib import Path

def fix_syntax_error():
    pipeline_path = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py")
    
    print("🔧 Fixing syntax error in pipeline...")
    
    # Read current pipeline
    with open(pipeline_path, 'r') as f:
        content = f.read()
    
    # Fix escaped characters
    content = content.replace("scores\\['E1'\\] \\+= 7", "scores['E1'] += 7")
    
    print("   ✅ Fixed escaped characters in Chinese scoring line")
    
    # Write fixed pipeline
    with open(pipeline_path, 'w') as f:
        f.write(content)
    
    print("✅ Syntax error fixed!")

if __name__ == "__main__":
    fix_syntax_error()