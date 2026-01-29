import json
from glob import glob
import os
import re
from collections import defaultdict

from openai import AzureOpenAI
from tqdm import tqdm
import time
import ast
from key import OPENAI_KEY

client = AzureOpenAI(
    api_key=OPENAI_KEY,
    api_version="2024-10-21",
    azure_endpoint="https://hkust.azure-api.net"
)

question = """Please first identify the number of subfigures possible described by this caption. Then, split the subcaption based on the number of subfigures you identified. Please return the number of subfigures and the splitted subcaptions only. Please do not summarize the subcaptions and only do the splitting and complete the sentence. Return a json dictionary with {num_subcaption: , sub_list:[]}. The length of the sub_list should match the num_subcaption. If there is no subcaptions, return a json dictionary with {num_subcaption: 1, sub_list:[<original_caption>]}. \n <cap>"""

def parse_json(json_output):
    """Parse JSON from potential markdown fencing."""
    lines = json_output.splitlines()
    for i, line in enumerate(lines):
        if line == "```json":
            json_output = "\n".join(lines[i+1:])
            json_output = json_output.split("```")[0]
            break
    return json_output

def get_image_number(img_path):
    """Extract the numeric part from image path for sorting (e.g., 'img-4.jpeg' -> 4)."""
    basename = os.path.basename(img_path)
    match = re.search(r'img-(\d+)', basename)
    if match:
        return int(match.group(1))
    return 0

def split_caption_with_api(cap):
    """Call API to split a caption into subcaptions."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an experienced expert in echocardiography, and you are especially good at detecting and splitting subcaptions."
                },
                {"role": "user", "content": [
                    {"type": "text", "text": question.replace("<cap>", cap)},
                ]}
            ]
        )
        pred = response.choices[0].message.content
        returned_dict = ast.literal_eval(parse_json(pred))
        return returned_dict
    except Exception as e:
        print(f"API error: {e}")
        time.sleep(10)
        return None

def group_images_by_caption(md_list):
    """
    Group consecutive images that share the same caption.
    Returns a list of groups, where each group is a dict with:
    - 'images': list of image paths
    - 'caption': the shared caption
    """
    # Convert to list of (img_path, caption) sorted by image number
    items = [(img, cap) for img, cap in md_list.items()]
    items.sort(key=lambda x: get_image_number(x[0]))
    
    groups = []
    current_group = None
    
    for img_path, caption in items:
        if current_group is None:
            current_group = {'images': [img_path], 'caption': caption}
        elif caption == current_group['caption']:
            # Same caption as previous, add to current group
            current_group['images'].append(img_path)
        else:
            # Different caption, start a new group
            groups.append(current_group)
            current_group = {'images': [img_path], 'caption': caption}
    
    # Don't forget the last group
    if current_group is not None:
        groups.append(current_group)
    
    return groups

# Find all _icp.json files in the Intermediate directory
all_md_jsons = glob("../Intermediate/**/*_icp.json", recursive=True)

for md_json in all_md_jsons:
    
    base_name = os.path.basename(md_json).replace("_icp.json", "")
    dir_name = os.path.dirname(md_json)
    save_splitted_icp_json_path = dir_name + "/" + base_name + "_icp_splited.json"
    
    if os.path.exists(save_splitted_icp_json_path):
        print(f"Skipping {base_name} - already processed")
        continue

    with open(md_json, encoding='utf-8') as f:
        md_list = json.load(f)

    # Group images by shared captions
    groups = group_images_by_caption(md_list)
    print(f"\nProcessing {base_name}: {len(md_list)} images grouped into {len(groups)} caption groups")
    
    img_text_split_pair = {}
    
    for group in tqdm(groups, desc="Processing caption groups"):
        images = group['images']
        caption = group['caption']
        num_images = len(images)
        
        # Call API to split the caption
        result = split_caption_with_api(caption)
        
        if result is None:
            # API failed, treat as single caption for each image
            for img in images:
                img_text_split_pair[img] = {
                    "num_subcaption": 1,
                    "sub_list": [caption],
                    "pre_split_by_ocr": num_images > 1
                }
            continue
        
        num_subcaptions = result.get("num_subcaption", 1)
        sub_list = result.get("sub_list", [caption])
        
        # Case 1: Multiple images share a caption AND number of subcaptions matches number of images
        # This means OCR already split the figure, so assign each subcaption to corresponding image
        if num_images > 1 and num_subcaptions == num_images:
            print(f"  -> OCR pre-split detected: {num_images} images match {num_subcaptions} subcaptions")
            for i, img in enumerate(images):
                img_text_split_pair[img] = {
                    "num_subcaption": 1,  # Each image is already a single subfigure
                    "sub_list": [sub_list[i]],
                    "pre_split_by_ocr": True,
                    "original_caption": caption
                }
        
        # Case 2: Multiple images share a caption but subcaptions don't match image count
        # This might be a partial split or different scenario - treat each image as having full caption info
        elif num_images > 1 and num_subcaptions != num_images:
            print(f"  -> Partial match: {num_images} images, {num_subcaptions} subcaptions - keeping original split info")
            for img in images:
                img_text_split_pair[img] = {
                    "num_subcaption": num_subcaptions,
                    "sub_list": sub_list,
                    "pre_split_by_ocr": False,
                    "shared_caption_group_size": num_images
                }
        
        # Case 3: Single image with its caption (normal case)
        else:
            img_text_split_pair[images[0]] = {
                "num_subcaption": num_subcaptions,
                "sub_list": sub_list,
                "pre_split_by_ocr": False
            }
        
        # Save progress
        with open(save_splitted_icp_json_path, "w", encoding='utf-8') as f:
            json.dump(img_text_split_pair, f, indent=4, ensure_ascii=False)

    print(f"Completed {base_name}: {len(img_text_split_pair)} entries saved")
