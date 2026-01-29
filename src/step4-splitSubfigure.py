import json
from glob import glob
import os
import re
import ast
import shutil

from openai import OpenAI
from PIL import Image
import base64
from tqdm import tqdm
from qwen_vl_utils import smart_resize
from copy import deepcopy
from key import QWEN_KEY

question = "You are given a figure with <num_caps> subfigures. Outline the position of all subfigures in this figure and output all the coordinates in JSON format. Note that all subfigures is most likely to cover all the space in the figure. Name each detected subfigure with a letter consistent with the annotation in image. If there are no subfigures, return 'None'. Please output <num_caps> bounding boxes."

min_pixels = 128 * 28 * 28
max_pixels = 2048 * 28 * 28

client = OpenAI(
    api_key=QWEN_KEY,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def inference_with_api(image_path, prompt, sys_prompt="As an AI assistant, you specialize in accurate image object detection, and you are an echocardiography expert who knows how to split subfigures.", model_id="qwen2.5-vl-72b-instruct", min_pixels=512*28*28, max_pixels=2048*28*28):
    base64_image = encode_image(image_path)
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": sys_prompt}]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "min_pixels": min_pixels,
                    "max_pixels": max_pixels,
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]
    completion = client.chat.completions.create(
        model=model_id,
        messages=messages,
    )
    return completion.choices[0].message.content

def plot_bounding_boxes(im, bounding_boxes, input_width, input_height, savepath):
    """
    Plots bounding boxes on an image with markers for each a name, using PIL, normalized coordinates, and different colors.
    """
    ori_img = im
    width, height = ori_img.size
    bounding_boxes = parse_json(bounding_boxes)

    try:
        json_output = ast.literal_eval(bounding_boxes)
    except Exception as e:
        end_idx = bounding_boxes.rfind('"}') + len('"}')
        truncated_text = bounding_boxes[:end_idx] + "]"
        json_output = ast.literal_eval(truncated_text)
    
    ori_savepath = savepath
    save_list = []
    
    for i, bounding_box in enumerate(json_output):
        abs_y1 = int(bounding_box["bbox_2d"][1] / input_height * height)
        abs_x1 = int(bounding_box["bbox_2d"][0] / input_width * width)
        abs_y2 = int(bounding_box["bbox_2d"][3] / input_height * height)
        abs_x2 = int(bounding_box["bbox_2d"][2] / input_width * width)

        if abs_x1 > abs_x2:
            abs_x1, abs_x2 = abs_x2, abs_x1
        if abs_y1 > abs_y2:
            abs_y1, abs_y2 = abs_y2, abs_y1
        
        img = deepcopy(ori_img)
        img = img.crop((abs_x1, abs_y1, abs_x2, abs_y2))
        savepath = ori_savepath.replace(".png", "_" + str(i) + ".png")
        save_list.append(savepath)
        img.save(savepath)
        del img
    
    return save_list

def parse_json(json_output):
    """Parsing out the markdown fencing."""
    lines = json_output.splitlines()
    for i, line in enumerate(lines):
        if line == "```json":
            json_output = "\n".join(lines[i+1:])
            json_output = json_output.split("```")[0]
            break
    return json_output

# Find all _icp_splited.json files in the Intermediate directory
all_md_jsons = glob("../Intermediate/**/*_icp_splited.json", recursive=True)

figure_count = 0
for md_json in all_md_jsons:
    print(f"\nProcessing: {md_json}")
    base_name = os.path.basename(md_json).replace("_icp_splited.json", "")
    folder_name = os.path.dirname(md_json)
    img_folder = f"{folder_name}"
    save_splitted_icp_json_path = f"{folder_name}/{base_name}_icp_aligned.json"
    save_img_folder = f"{folder_name}/{base_name}_splitted_images"
    os.makedirs(save_img_folder, exist_ok=True)

    with open(md_json, encoding='utf-8') as f:
        md_list = json.load(f)

    splitted_list = []
    recheck_list = []
    
    # Statistics
    pre_split_count = 0
    needs_split_count = 0
    single_count = 0
    
    for img_name, cap in tqdm(md_list.items(), desc="Processing images"):
        num_subfigure = cap.get("num_subcaption", 1)
        sub_list = cap.get("sub_list", [])
        pre_split_by_ocr = cap.get("pre_split_by_ocr", False)
        
        image_path = img_folder + "/" + img_name
        
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"  Warning: Image not found: {image_path}")
            continue
        
        # Case 1: Image was already pre-split by OCR (num_subcaption=1, pre_split_by_ocr=True)
        # Just copy the image and use its assigned caption directly
        if pre_split_by_ocr and num_subfigure == 1:
            pre_split_count += 1
            dest_path = save_img_folder + "/" + os.path.basename(img_name)
            shutil.copy(image_path, dest_path)
            new_image = {
                "image": dest_path,
                "caption": sub_list[0] if sub_list else ""
            }
            splitted_list.append(new_image)
        
        # Case 2: Single subfigure (no splitting needed)
        elif num_subfigure == 1:
            single_count += 1
            dest_path = save_img_folder + "/" + os.path.basename(img_name)
            shutil.copy(image_path, dest_path)
            new_image = {
                "image": dest_path,
                "caption": sub_list[0] if sub_list else ""
            }
            splitted_list.append(new_image)
        
        # Case 3: Multiple subfigures - need to split the image
        elif num_subfigure > 1:
            needs_split_count += 1
            try:
                image = Image.open(image_path)
                image_name_clean = os.path.basename(image_path).replace(".jpeg", "").replace(".png", "")
                width, height = image.size
                input_height, input_width = smart_resize(height, width, min_pixels=min_pixels, max_pixels=max_pixels)
                
                cap_question = question.replace("<num_caps>", str(num_subfigure))
                response = inference_with_api(image_path, cap_question, min_pixels=min_pixels, max_pixels=max_pixels)
                save_list = plot_bounding_boxes(image, response, input_width, input_height, f"{save_img_folder}/{image_name_clean}.png")
                
                if len(save_list) == num_subfigure:
                    # Successfully split into expected number of subfigures
                    for i, sub in enumerate(sub_list):
                        new_image = {"image": save_list[i], "caption": sub}
                        splitted_list.append(new_image)
                else:
                    # Mismatch in split count - add to recheck
                    recheck_image = {
                        "image": image_path,
                        "caption": cap,
                        "response": response,
                        "save_list": save_list,
                        "expected_subfigures": num_subfigure,
                        "actual_splits": len(save_list)
                    }
                    recheck_list.append(recheck_image)
                    
            except Exception as e:
                recheck_image = {
                    "image": image_path,
                    "caption": cap,
                    "error": str(e)
                }
                recheck_list.append(recheck_image)
                print(f"  Error in {image_path}: {e}")
                continue
        
        # Save progress periodically
        with open(save_splitted_icp_json_path, "w", encoding='utf-8') as f:
            json.dump(splitted_list, f, indent=4, ensure_ascii=False)
        with open(save_splitted_icp_json_path.replace(".json", "_recheck.json"), "w", encoding='utf-8') as f:
            json.dump(recheck_list, f, indent=4, ensure_ascii=False)
    
    print(f"\nCompleted {base_name}:")
    print(f"  - Pre-split by OCR: {pre_split_count}")
    print(f"  - Single subfigures: {single_count}")
    print(f"  - Needed vision split: {needs_split_count}")
    print(f"  - Total aligned: {len(splitted_list)}")
    print(f"  - Need recheck: {len(recheck_list)}")

print(f"\nTotal figure groups processed: {figure_count}")
