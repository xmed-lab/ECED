import json
from glob import glob
import os
import re
from openai import AzureOpenAI
from tqdm import tqdm
import json
from glob import glob
import base64
import time
from key import OPENAI_KEY

client = AzureOpenAI(
    api_key=OPENAI_KEY,
    api_version="2024-10-21",
    azure_endpoint="https://hkust.azure-api.net"
)
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Find all aligned and text json files in the Intermediate directory
all_icp_jsons=glob("../Intermediate/**/*_icp_aligned.json",recursive=True)
all_text_jsons=glob("../Intermediate/**/*_text.json",recursive=True)

# Create final_output directory if it doesn't exist
os.makedirs("../final_output", exist_ok=True)


question="You are given a paragraph, mostly related to echocardiography and related echocardiography descriptions. Please give five to ten keywords that best describe the paragraph. These ten keywords should involve keywords in potential diseases, echocardiography modalities, echocardiography views, diagnositic methods, and other related information. These keywords should represent the paragraph as comprehensive as possible. If the paragraph is long, you can use more keywords. You only need to return these keywords. Use the format:'keywords1\nkeywords2\n...'."


for md_json in all_icp_jsons:
    
    base_name=os.path.basename(md_json).replace("_icp_aligned.json","")
    save_path=os.path.join("../final_output", base_name + "_icp_aligned_wkw.json")
    img_folder=os.path.dirname(md_json)

    with open(md_json) as f:
        md_list=json.load(f)

    pairs_with_keyword=[]
    for icp in tqdm(md_list):
        img_name=icp["image"]
        caption=icp["caption"]

        content=[]
        text=question
        text+="Here is paragraph: \n"
        text+=caption
        content.append({"type": "text", "text": text})
        base64_image = encode_image(img_name)
        content.append({"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"}
                    })
        try:
            response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an experienced expert in echocardiography and especially good at summarizing the key concepts represented in the texts and echocardiography."
                            },
                            {"role": "user", "content": content}
                        ]
                    )
        except:
            time.sleep(10)
            continue

        pred=response.choices[0].message.content
        icp["keywords_raw"]=pred
        try:
            icp["keywords"]=pred.split("\n")
            # remove the space before and after the keywords
            icp["keywords"]=[i.strip() for i in icp["keywords"]]
        except:
            icp["keywords"]=[]
        pairs_with_keyword.append(icp)
        with open(save_path, "w") as f:
            json.dump(pairs_with_keyword,f,indent=4)


for md_json in all_text_jsons:
    
    base_name=os.path.basename(md_json).replace("_text.json","")
    save_path=os.path.join("../final_output", base_name + "_text_wkw.json")

    with open(md_json) as f:
        md_list=json.load(f)

    pairs_with_keyword=[]
    for icp in tqdm(md_list):
        new_dict={}
        new_dict["text"]=icp
        caption=icp

        content=[]
        text=question
        text+="Here is paragraph: \n"
        text+=caption
        content.append({"type": "text", "text": text})
        try:
            response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an experienced expert in echocardiography and especially good at summarizing the key concepts represented in the texts and echocardiography."
                            },
                            {"role": "user", "content": content}
                        ]
                    )
        except:
            time.sleep(10)
            continue

        pred=response.choices[0].message.content



        new_dict["keywords_raw"]=pred
        try:
            new_dict["keywords"]=pred.split("\n")
            # remove the space before and after the keywords
            new_dict["keywords"]=[i.strip() for i in new_dict["keywords"]]
        except:
            new_dict["keywords"]=[]
        pairs_with_keyword.append(new_dict)
        with open(save_path, "w") as f:
            json.dump(pairs_with_keyword,f,indent=4)