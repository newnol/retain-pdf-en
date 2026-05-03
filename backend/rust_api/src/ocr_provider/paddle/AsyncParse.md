# PaddleOCR-VL-1.5 Service Deployment Call Examples and API Introduction

>
>
>
> [PaddleOCR Open Source Project GitHub Address](https://github.com/PaddlePaddle/PaddleOCR/tree/release/3.3), this service is **built based on the PaddleOCR-VL model of this open source project**.
>
> **Version Notes**: The current corresponding **PaddleX version is 3.4.0** and **PaddlePaddle version is 3.2.1** on the PaddleOCR official website.

## 1. PaddleOCR-VL-1.5 Introduction

On January 29, 2026, we released **PaddleOCR-VL-1.5** based on PaddleOCR-VL. PaddleOCR-VL-1.5 not only significantly improved the evaluation set OmniDocBench v1.5 with 94.5% accuracy, but also innovatively supported irregular bounding box positioning, making PaddleOCR-VL-1.5 perform excellently in real-world scenarios such as scanning, tilting, bending, screen capture, and complex lighting. Additionally, the model has added seal recognition and text detection/recognition capabilities, with key metrics continuing to lead.

### **Key Metrics:**

![](https://paddle-model-ecology.bj.bcebos.com/paddlex/demo_image/paddleocr-vl-1.5_metrics.png)

The following figure shows the overall workflow and new capabilities of PaddleOCR-VL-1.5:

![](https://paddle-model-ecology.bj.bcebos.com/paddlex/demo_image/PaddleOCR-VL-1.5.png)

## 2. API Documentation

Please refer to the [documentation](https://ai.baidu.com/ai-doc/AISTUDIO/Xmjclapam)

## 3. Service Call Example (Python)

```
# Please make sure the requests library is installed
# pip install requests
import base64
import os
import requests

# For API_URL and TOKEN, visit [PaddleOCR Official Website](https://aistudio.baidu.com/paddleocr/task) to get from the API call examples.
API_URL = "<your url>"
TOKEN = "<access token>"

file_path = "<local file path>"

with open(file_path, "rb") as file:
    file_bytes = file.read()
    file_data = base64.b64encode(file_bytes).decode("ascii")

headers = {
    "Authorization": f"token {TOKEN}",
    "Content-Type": "application/json"
}

required_payload = {
    "file": file_data,
    "fileType": <file type>,  # For PDF documents, set `fileType` to 0; for images, set `fileType` to 1
}

optional_payload = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}

payload = {**required_payload, **optional_payload}

response = requests.post(API_URL, json=payload, headers=headers)
print(response.status_code)
assert response.status_code == 200
result = response.json()["result"]

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

for i, res in enumerate(result["layoutParsingResults"]):
    md_filename = os.path.join(output_dir, f"doc_{i}.md")
    with open(md_filename, "w", encoding="utf-8") as md_file:
        md_file.write(res["markdown"]["text"])
    print(f"Markdown document saved at {md_filename}")
    for img_path, img in res["markdown"]["images"].items():
        full_img_path = os.path.join(output_dir, img_path)
        os.makedirs(os.path.dirname(full_img_path), exist_ok=True)
        img_bytes = requests.get(img).content
        with open(full_img_path, "wb") as img_file:
            img_file.write(img_bytes)
        print(f"Image saved to: {full_img_path}")
    for img_name, img in res["outputImages"].items():
        img_response = requests.get(img)
        if img_response.status_code == 200:
            # Save image to local
            filename = os.path.join(output_dir, f"{img_name}_{i}.jpg")
            with open(filename, "wb") as f:
                f.write(img_response.content)
            print(f"Image saved to: {filename}")
        else:
            print(f"Failed to download image, status code: {img_response.status_code}")
```

For the main operations provided by the service:

- HTTP request method is POST.
- Request body and response body are both JSON data (JSON objects).
- When the request is processed successfully, the response status code is `200`, and the response body properties are as follows:

| Name | Type | Description |
| --- | --- | --- |
| `logId` | `string` | UUID of the request. |
| `errorCode` | `integer` | Error code. Fixed at `0`. |
| `errorMsg` | `string` | Error description. Fixed at `"Success"`. |
| `result` | `object` | Operation result. |

- When the request is not processed successfully, the response body properties are as follows:

| Name | Type | Description |
| --- | --- | --- |
| `logId` | `string` | UUID of the request. |
| `errorCode` | `integer` | Error code. Same as the response status code. |
| `errorMsg` | `string` | Error description. |

The main operations provided by the service are as follows:

- **`infer`**

Perform layout parsing.

`POST /layout-parsing`

## 4. Request Parameter Descriptions

| Name | Parameter | Type | Description | Required |
| --- | --- | --- | --- | --- |
| `Input File` | `file` | `string` | URL of an image file or PDF file accessible by the server, or Base64-encoded content of the above file types. By default, for PDF files exceeding 100 pages, only the first 100 pages will be processed. To remove the page limit, add the following configuration to the pipeline config file:

`Serving:
  extra:
    max_num_input_imgs: null`
 | Yes |
| `File Type` | `fileType` | `integer`｜`null` | File type. `0` for PDF files, `1` for image files. If the request body does not have this property, the file type will be inferred from the URL. | No |
| `Image Orientation Correction` | `useDocOrientationClassify` | `boolean` | `null` | Whether to use the text image orientation correction module during inference. When enabled, it can automatically identify and correct images at 0°, 90°, 180°, 270°. | No |
| `Image Distortion Correction` | `useDocUnwarping` | `boolean` | `null` | Whether to use the text image correction module during inference. When enabled, it can automatically correct distorted images, such as wrinkles, tilting, etc. | No |
| `Layout Analysis` | `useLayoutDetection` | `boolean` | `null` | Whether to use the layout region detection and sorting module during inference. When enabled, it can automatically detect and sort different regions in the document. | No |
| `Chart Recognition` | `useChartRecognition` | `boolean` | `null` | Whether to use the chart parsing module during inference. When enabled, it can automatically parse charts (such as bar charts, pie charts, etc.) in the document and convert them to table format for easy viewing and editing of data. | No |
| `Layout Region Filter Strength` | `layoutThreshold` | `number` | `object` | `null` | Layout model score threshold. Any floating-point number between `0-1`. If not set, the pipeline initialization value will be used, defaulting to `0.5`. | No |
| `NMS Post-processing` | `layoutNms` | `boolean` | `null` | Whether to use post-processing NMS for layout detection. When enabled, it will automatically remove duplicate or highly overlapping region boxes. | No |
| `Expansion Ratio` | `layoutUnclipRatio` | `number` | `array` | `object` | `null` | Expansion ratio for layout region detection model bounding boxes. Any floating-point number greater than `0`. If not set, the pipeline initialization value will be used, defaulting to `1.0`. | No |
| `Layout Region Detection Overlap Box Filter Mode` | `layoutMergeBboxesMode` | `string` | `object` | `null` |
• **large**: When set to large, for overlapping and containing detection boxes in the model output, only the outermost largest box is kept, and the inner overlapping boxes are deleted.
• **small**: When set to small, for overlapping and containing detection boxes in the model output, only the inner contained small box is kept, and the outer overlapping boxes are deleted.
• **union**: No box filtering is performed, both inner and outer boxes are kept. If not set, the pipeline initialization value will be used, defaulting to `large`. | No |
| `Layout Detection Result Geometry` | `layoutShapeMode` | `string` | `null` | Specifies the geometric shape representation mode for layout detection results. This parameter determines how detection region (e.g., text blocks, images, tables) boundaries are calculated and displayed. Available values are `rect` (rectangle), `quad` (quadrilateral), `poly` (polygon), and `auto` (automatic). Defaults to `auto`. | No |
| `Prompt Type Setting` | `promptLabel` | `string` | `null` | VL model prompt type setting, effective only when `useLayoutDetection=False`. Available values are `ocr`, `formula`, `table`, and `chart`, defaulting to `ocr`. | No |
| `Repetition Suppression Strength` | `repetitionPenalty` | `number` | `null` | Increase when repeated text or repeated table content appears in results. | No |
| `Recognition Stability` | `temperature` | `number` | `null` | Decrease when results are unstable or have obvious hallucinations; slightly increase when there are many missed recognitions or repetitions. | No |
| `Result Confidence Range` | `topP` | `number` | `null` | Decrease when results are divergent or not confident enough, making the model more conservative. | No |
| `Minimum Image Size` | `minPixels` | `number` | `null` | Increase when input images are too small and text is unclear; generally no adjustment needed. | No |
| `Maximum Image Size` | `maxPixels` | `number` | `null` | Decrease when input images are particularly large, processing slows down or GPU memory pressure is high. | No |
| `Formula Number Display` | `showFormulaNumber` | `boolean` | Whether the output Markdown text includes formula numbers. | No |
| `Restructure Multi-page Results` | `restructurePages` | `boolean` | Restructure multi-page PDF parsing results for cross-page table merging and paragraph heading level recognition. Defaults to `False`. | No |
| `Cross-page Table Merging` | `mergeTables` | `boolean` | When enabled, identifies cross-page tables and merges them into one. Effective only when `useLayoutDetection=False`. Defaults to `True`. | No |
| `Paragraph Heading Level Recognition` | `relevelTitles` | `boolean` | When enabled, recognizes paragraph heading levels. Effective only when `useLayoutDetection=False`. Defaults to `True`. | No |
| `Markdown Beautification` | `prettifyMarkdown` | `boolean` | Whether to output beautified Markdown text. | No |
| `Visualization` | `visualize` | `boolean` | `null` | Supports returning visualization result images and intermediate images during processing. Enabling this will increase result return time.
• Pass `true`: Return images.
• Pass `false`: Don't return images.
• If not provided or passed as `null` in the request body: Follow the `Serving.visualize` setting in the pipeline config file. For example, adding the following field in the pipeline config:

`Serving:
  visualize: False`
 will default to not returning images. The `visualize` parameter in the request body can override the default behavior. If not set in both request body and config file (or `null` in request body and not set in config file), images are returned by default. | No |

When the request is processed successfully, the `result` in the response body has the following properties:

| Name | Type | Description |
| --- | --- | --- |
| `layoutParsingResults` | `array` | Layout parsing results. Array length is 1 (for image input) or the actual number of processed document pages (for PDF input). For PDF input, each element in the array represents the result of each actually processed page in the PDF file. |
| `dataInfo` | `object` | Input data information. |

Each element in `layoutParsingResults` is an `object` with the following properties:

| Name | Type | Description |
| --- | --- | --- |
| `prunedResult` | `object` | A simplified version of the `res` field in the JSON representation of the `predict` method's generated result, with `input_path` and `page_index` fields removed. |
| `markdown` | `object` | Markdown result. |
| `outputImages` | `object` | `null` | See the `img` property description of the prediction result. Images are in JPEG format, encoded with Base64. |
| `inputImage` | `string` | `null` | Input image. Image is in JPEG format, encoded with Base64. |

`markdown` is an `object` with the following properties:

| Name | Type | Description |
| --- | --- | --- |
| `text` | `string` | Markdown text. |
| `images` | `object` | Key-value pairs of Markdown image relative paths and Base64-encoded images. |

- **`restructurePages`**

Restructure multi-page results (optional).

`POST /restructure-pages`

- The request body properties are as follows:

| Name | Parameter | Type | Description | Required |
| --- | --- | --- | --- | --- |
| `Cross-page Table Merging` | `mergeTables` | `boolean` | When enabled, identifies cross-page tables and merges them into one. Effective only when `useLayoutDetection=False`. Defaults to `True`. | No |
| `Paragraph Heading Level Recognition` | `relevelTitles` | `boolean` | When enabled, recognizes paragraph heading levels. Effective only when `useLayoutDetection=False`. Defaults to `True`. | No |
| `Restructure Multi-page Results` | `concatenatePages` | `boolean` | Restructure multi-page PDF parsing results for cross-page table merging and paragraph heading level recognition. Defaults to `False`. | No |
| `Markdown Beautification` | `prettifyMarkdown` | `boolean` | Whether to output beautified Markdown text. | No |
| `Formula Number Display` | `showFormulaNumber` | `boolean` | Whether the output Markdown text includes formula numbers. | No |

Each element in `pages` is an `object` with the following properties:

| Name | Type | Description |
| --- | --- | --- |
| `prunedResult` | `object` | The `prunedResult` object returned by the corresponding `infer` operation. |
| `markdownImages` | `object`|`null` | The `images` property of the `markdown` object returned by the corresponding `infer` operation. |

When the request is processed successfully, the `result` in the response body has the following properties:

| Name | Type | Description |
| --- | --- | --- |
| `layoutParsingResults` | `array` | Restructured layout parsing results. Each element contains fields as described in the `infer` operation result description (excluding visualization result images and intermediate images). |

For the returned data structure and field descriptions, please refer to the [documentation](https://www.paddleocr.ai/latest/version3.x/pipeline_usage/PaddleOCR-VL.html).

**Note**: If you encounter any issues during use, please feel free to submit feedback in the [issue](https://github.com/PaddlePaddle/PaddleOCR/issues) section.

# Async Call Code

# Please make sure the requests library is installed
# pip install requests
import json
import os
import requests
import sys
import time

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = "6e580446746aea4dc442c02f59d1575809d5f77b"
MODEL = "PaddleOCR-VL"

file_path = "<local file path or file url>"

headers = {
    "Authorization": f"bearer {TOKEN}",
}

optional_payload = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}

print(f"Processing file: {file_path}")

if file_path.startswith("http"):
    # URL Mode
    headers["Content-Type"] = "application/json"
    payload = {
        "fileUrl": file_path,
        "model": MODEL,
        "optionalPayload": optional_payload
    }
    job_response = requests.post(JOB_URL, json=payload, headers=headers)
else:
    # Local File Mode
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
        
    data = {
        "model": MODEL,
        "optionalPayload": json.dumps(optional_payload)
    }
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        job_response = requests.post(JOB_URL, headers=headers, data=data, files=files)

print(f"Response status: {job_response.status_code}")
if job_response.status_code != 200:
    print(f"Response content: {job_response.text}")

assert job_response.status_code == 200
jobId = job_response.json()["data"]["jobId"]
print(f"Job submitted successfully. job id: {jobId}")
print("Start polling for results")

jsonl_url = ""
while True:
    job_result_response = requests.get(f"{JOB_URL}/{jobId}", headers=headers)
    assert job_result_response.status_code == 200
    state = job_result_response.json()["data"]["state"]
    if state == 'pending':
        print("The current status of the job is pending")
    elif state == 'running':
        try:
            total_pages = job_result_response.json()['data']['extractProgress']['totalPages']
            extracted_pages = job_result_response.json()['data']['extractProgress']['extractedPages']
            print(f"The current status of the job is running, total pages: {total_pages}, extracted pages: {extracted_pages}")
        except KeyError:
             print("The current status of the job is running...")
    elif state == 'done':
        extracted_pages = job_result_response.json()['data']['extractProgress']['extractedPages']
        start_time = job_result_response.json()['data']['extractProgress']['startTime']
        end_time = job_result_response.json()['data']['extractProgress']['endTime']
        print(f"Job completed, successfully extracted pages: {extracted_pages}, start time: {start_time}, end time: {end_time}")
        jsonl_url = job_result_response.json()['data']['resultUrl']['jsonUrl']
        break
    elif state == "failed":
        error_msg = job_result_response.json()['data']['errorMsg']
        print(f"Job failed, failure reason: {error_msg}")
        sys.exit()

    time.sleep(5)

if jsonl_url:
    jsonl_response = requests.get(jsonl_url)
    jsonl_response.raise_for_status()
    lines = jsonl_response.text.strip().split('\n')
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    page_num = 0
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        for i, res in enumerate(result["layoutParsingResults"]):
            md_filename = os.path.join(output_dir, f"doc_{page_num}.md")
            with open(md_filename, "w", encoding="utf-8") as md_file:
                md_file.write(res["markdown"]["text"])
            print(f"Markdown document saved at {md_filename}")
            for img_path, img in res["markdown"]["images"].items():
                full_img_path = os.path.join(output_dir, img_path)
                os.makedirs(os.path.dirname(full_img_path), exist_ok=True)
                img_bytes = requests.get(img).content
                with open(full_img_path, "wb") as img_file:
                    img_file.write(img_bytes)
                print(f"Image saved to: {full_img_path}")
            for img_name, img in res["outputImages"].items():
                img_response = requests.get(img)
                if img_response.status_code == 200:
                    # Save image to local
                    filename = os.path.join(output_dir, f"{img_name}_{page_num}.jpg")
                    with open(filename, "wb") as f:
                        f.write(img_response.content)
                    print(f"Image saved to: {filename}")
                else:
                    print(f"Failed to download image, status code: {img_response.status_code}")
            page_num += 1
