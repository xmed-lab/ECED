# [MICCAI 2025] Multi-Agent Collaboration for Integrating Echocardiography Expertise in Multi-Modal Large Language Models

# TODO
We will complete the TODO list in the following weeks.
- [] Release the book source and license information.
- [] Release the pipeline code.


# Required API Keys

- [Mistral OCR API key](https://mistral.ai/)
- [Azure OpenAI API key](https://azure.microsoft.com/en-us/services/openai/)
- [Qwen API key](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)


## Overview

This automatic pipeline converts Echocardiography PDFs to Concept-Indexed Databases (EchoCardiography Expertise Database).
- Images with their captions
- Pure text content
- Subfigure detection and splitting
- Medical keywords for searchability



## Installation

### 1. Clone the Repository


### 2. Install Dependencies
```bash
pip install mistralai
pip install openai
pip install pillow
pip install pandas
pip install tqdm
pip install qwen-vl-utils
```

### 3. Create API Key Configuration
Create a `key.py` file in the project root:
```python
MISTRAL_KEY = "your-mistral-api-key"
OPENAI_KEY = "your-azure-openai-api-key"
QWEN_KEY = "your-qwen-api-key"
```

**⚠️ Security Note:** Never commit `key.py` to version control. Add it to `.gitignore`.

---

## Directory Structure

```
release_v1/
├── step1-mistral_ocr.py
├── step2-rawContentSplit.py
├── step3-checkSplitSubcaption.py
├── step4-splitSubfigure.py
├── step5-cleanTextandKeywords.py
├── key.py (create this - not in repo)
├── Todo/
│   ├── ENG/
│   │   ├── Guideline/
│   │   └── Textbook/
│   └── CHN/
│       ├── Guideline/
│       └── Textbook/
├── Intermediate/
│   └── [Generated during processing]
└── final_output/
    └── [Final results with keywords]
```

---

## Usage

### Running the Complete Pipeline

Execute steps sequentially:

```bash
# Step 1: OCR Processing
python step1-mistral_ocr.py

# Step 2: Content Splitting
python step2-rawContentSplit.py

# Step 3: Subcaption Detection
python step3-checkSplitSubcaption.py

# Step 4: Subfigure Splitting
python step4-splitSubfigure.py

# Step 5: Keyword Extraction
python step5-cleanTextandKeywords.py
```

### Input Requirements

Place PDF files in the appropriate directories:
- English Guidelines: `./Todo/ENG/Guideline/`
- English Textbooks: `./Todo/ENG/Textbook/`
- Chinese Guidelines: `./Todo/CHN/Guideline/`
- Chinese Textbooks: `./Todo/CHN/Textbook/`

### Output Structure

Final outputs are stored in `./final_output/` with the following structure:
- Image-caption pairs with keywords
- Text content with keywords
- Split subfigure images
- Recheck files for manual validation

## License

MIT License.
Copyright (c) 2025 The Hong Kong University of Science and Technology

---

## Contact

Contact yqinar@connect.ust.hk for any questions or feedback.
