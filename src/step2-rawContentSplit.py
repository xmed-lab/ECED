import json
from glob import glob
import os
import re

# Pattern to match figure captions like "Figure 1.4.", "Fig. 2.1", "TABLE 8.3", etc.
FIGURE_CAPTION_PATTERN = re.compile(
    r"^(Figure|Fig\.|Fig|TABLE|Table|图)\s*\d+[\.\-]?\d*[\.\-]?\d*\.?\s*",
    re.IGNORECASE
)

# Pattern to detect image references
IMAGE_REF_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

def clean_caption(caption_str):
    """Clean and normalize a caption string."""
    caption_str = caption_str.strip()
    # Remove leading/trailing whitespace and newlines
    caption_str = re.sub(r'\s+', ' ', caption_str)
    return caption_str

def extract_figure_number(text):
    """Extract figure number from text like 'Figure 1.4. Description...' """
    match = FIGURE_CAPTION_PATTERN.match(text.strip())
    if match:
        return match.group(0).strip()
    return None

def find_caption_after_image(text, max_lines=5):
    """
    Find a figure caption in the text following an image.
    Returns the full caption if found, None otherwise.
    """
    lines = text.split('\n')
    caption_lines = []
    found_figure_start = False
    
    for i, line in enumerate(lines[:max_lines]):
        line = line.strip()
        if not line:
            continue
        
        # Skip if line is another image reference
        if IMAGE_REF_PATTERN.match(line):
            continue
        
        # Skip single letters like "A", "B", "C" (subfigure labels)
        if len(line) == 1 and line.isalpha():
            continue
            
        # Check if this line starts with a figure caption pattern
        if FIGURE_CAPTION_PATTERN.match(line):
            found_figure_start = True
            caption_lines.append(line)
            # Continue to get the full caption (may span multiple lines)
            for j in range(i + 1, min(len(lines), i + 10)):
                next_line = lines[j].strip()
                if not next_line:
                    continue
                # Stop if we hit another figure reference or image
                if FIGURE_CAPTION_PATTERN.match(next_line):
                    break
                if IMAGE_REF_PATTERN.match(next_line):
                    break
                # Stop if we hit a section header
                if next_line.startswith('#'):
                    break
                caption_lines.append(next_line)
            break
    
    if caption_lines:
        return clean_caption(' '.join(caption_lines))
    return None

def find_caption_before_image(text, max_lines=5):
    """
    Find a figure caption in the text preceding an image.
    Returns the full caption if found, None otherwise.
    """
    lines = text.strip().split('\n')
    lines = [l for l in lines if l.strip()]  # Remove empty lines
    
    if not lines:
        return None
    
    # Look at the last few lines before the image
    caption_lines = []
    for i in range(len(lines) - 1, max(len(lines) - max_lines - 1, -1), -1):
        line = lines[i].strip()
        
        # Skip if line is another image reference
        if IMAGE_REF_PATTERN.match(line):
            continue
            
        # Check if this line contains a figure caption pattern
        if FIGURE_CAPTION_PATTERN.search(line):
            # Found the start of a caption, collect from here to the end
            caption_lines = [lines[j].strip() for j in range(i, len(lines)) 
                           if lines[j].strip() and not IMAGE_REF_PATTERN.match(lines[j].strip())]
            break
    
    if caption_lines:
        return clean_caption(' '.join(caption_lines))
    return None

def is_valid_caption(caption):
    """Check if a caption is valid (not just noise or fragment)."""
    if not caption:
        return False
    
    # Must be at least 20 characters
    if len(caption) < 20:
        return False
    
    # Should not be just an image reference
    if IMAGE_REF_PATTERN.match(caption.strip()):
        return False
    
    # Should not contain table delimiters (likely a table, not a caption)
    if '|' in caption:
        return False
    
    # Should not start with common non-caption patterns
    skip_starts = ['#', 'Video ', 'SECTION ', 'REFERENCES', 'Copyright']
    for skip in skip_starts:
        if caption.strip().startswith(skip):
            return False
    
    return True

def extract_caption_text(caption):
    """Extract the descriptive text from a caption, removing figure number prefix."""
    # Remove the "Figure X.X." prefix but keep the description
    cleaned = FIGURE_CAPTION_PATTERN.sub('', caption).strip()
    # Remove leading punctuation
    cleaned = re.sub(r'^[\.\,\:\s]+', '', cleaned)
    return cleaned.strip()

# get all md jsons
all_md_jsons = glob("../Intermediate/**/*_mdlist.json", recursive=True)

total_icp_count = 0
for md_json in all_md_jsons:
    
    base_name = os.path.basename(md_json).replace("_mdlist.json", "")
    dir_name = os.path.dirname(md_json)
    img_folder = f"./{base_name}_images"
    save_icp_json_path = dir_name + "/" + base_name + "_icp.json"
    save_text_path = dir_name + "/" + base_name + "_text.json"

    with open(md_json, encoding='utf-8') as f:
        md_list = json.load(f)

    img_text_pair = {}
    pure_text_list = []
    
    # Process all content segments
    for content_seg in md_list:
        # Find all image references in the content segment
        images = [(match.group(), match.start(), match.end(), match.group(2)) 
                  for match in IMAGE_REF_PATTERN.finditer(content_seg)]
        
        if images:
            for img_match, start_pos, end_pos, img_name in images:
                full_path = img_folder + "/" + img_name
                
                # Strategy 1: Look for caption AFTER the image
                text_after = content_seg[end_pos:]
                caption = find_caption_after_image(text_after)
                
                # Strategy 2: If no caption found after, look BEFORE the image
                if not caption or not is_valid_caption(caption):
                    text_before = content_seg[:start_pos]
                    caption = find_caption_before_image(text_before)
                
                # Strategy 3: For images grouped together, the caption might be after the last image
                # Check if there are more images right after this one
                if not caption or not is_valid_caption(caption):
                    # Find the next non-image content
                    remaining = text_after
                    while True:
                        next_img = IMAGE_REF_PATTERN.search(remaining)
                        if next_img:
                            # Skip single-letter labels
                            text_between = remaining[:next_img.start()].strip()
                            if len(text_between) <= 2:
                                remaining = remaining[next_img.end():]
                                continue
                        break
                    caption = find_caption_after_image(remaining)
                
                # Validate and store the caption
                if caption and is_valid_caption(caption):
                    # Extract just the descriptive text
                    caption_text = extract_caption_text(caption)
                    if caption_text and len(caption_text) >= 15:
                        img_text_pair[full_path] = caption_text
        
        # Clean the content_seg by removing image references for pure text
        cleaned_seg = content_seg
        for img_match, _, _, _ in images:
            cleaned_seg = cleaned_seg.replace(img_match, "")
        cleaned_seg = cleaned_seg.strip()
        if cleaned_seg:
            pure_text_list.append(cleaned_seg)
    
    total_icp_count += len(img_text_pair)
    
    with open(save_text_path, "w", encoding='utf-8') as f:
        json.dump(pure_text_list, f, indent=4, ensure_ascii=False)
    
    with open(save_icp_json_path, "w", encoding='utf-8') as f:
        json.dump(img_text_pair, f, indent=4, ensure_ascii=False)
    
    print(f"Processed {base_name}: {len(img_text_pair)} image-caption pairs")

print(f"\nTotal image-caption pairs: {total_icp_count}")
