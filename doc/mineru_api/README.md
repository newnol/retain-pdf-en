MinerU provides two types of document parsing APIs to meet different scenario needs:

🎯 Precision Parsing API — Requires token application, supports single file/batch, tables/formulas/multi-format output
⚡ Agent Lightweight Parsing API — No login required, IP rate-limited to prevent abuse, designed specifically for AI Agent workflows
Mode Comparison
Comparison Dimension	🎯 Precision Parsing API	⚡ Agent Lightweight Parsing API
Token Required	✅ Yes	❌ No (IP rate-limited)
Endpoint	/api/v4/extract/task or /api/v4/file-urls/batch	/api/v1/agent/parse/url or /api/v1/agent/parse/file
Model Version	pipeline (default) / vlm (recommended) / MinerU-HTML	Fixed pipeline lightweight model
File Size Limit	≤ 200MB	≤ 10MB
Page Limit	≤ 600 pages	≤ 20 pages
Batch Support	✅ Yes (≤ 200 files)	❌ Single file
Output Format	Zip package containing Markdown, JSON, exportable to docx/html/latex	Markdown only (CDN link)
Invocation Method	Async (submit → poll)	Async (submit → poll)
🎯 Precision Parsing API
Requires token application, supports pipeline / vlm / MinerU-HTML models, both single file and batch are supported.

Overview
MinerU's Precision Parsing API is designed for complex documents that require high-precision, deep-level structured extraction. It can intelligently identify and process various complex layouts, multimodal content (such as tables, mathematical formulas, charts, images, multi-column layouts, etc.), converting document content into high-quality structured data.

Core Features:

Ultimate Precision: Provides industry-leading parsing accuracy, especially adept at handling non-standard and complex documents
Deep Structuring: Not just text extraction, but deep understanding of document layout and semantics, outputting structured data with rich hierarchical relationships
Multimodal Support: Comprehensive support for precise recognition and extraction of text, tables, images, formulas, and other content types
Complex Layout Adaptation: Effectively handles complex document scenarios such as scans, disordered layouts, watermark interference, etc.
File Limits:

Limit Item	Limit Value
Max File Size	200 MB
Max Pages	600 pages
Supported File Types	PDF, Images (png/jpg/jpeg/jp2/webp/gif/bmp), Doc, Docx, Ppt, PPTx
Single File Parsing
Create Parsing Task
Endpoint Description

Applicable for creating parsing tasks via API, users must first apply for a Token. Note:

Single file size cannot exceed 200MB, file pages cannot exceed 600 pages
Each account receives 2000 pages of highest priority parsing quota per day; pages exceeding 2000 are processed at lower priority
Due to network limitations, foreign URLs like github, aws may experience request timeouts
This endpoint does not support direct file upload
The header must include the Authorization field, formatted as Bearer + space + Token
Python request example (applicable for pdf, doc, ppt, image files):

import requests

token = "API token applied from official website"
url = "https://mineru.net/api/v4/extract/task"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
    "model_version": "vlm"
}

res = requests.post(url,headers=header,json=data)
print(res.status_code)
print(res.json())
print(res.json()["data"])
Python request example (applicable for html files):

import requests

token = "API token applied from official website"
url = "https://mineru.net/api/v4/extract/task"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "url": "https://****",
    "model_version": "MinerU-HTML"
}

res = requests.post(url,headers=header,json=data)
print(res.status_code)
print(res.json())
print(res.json()["data"])
CURL request example (applicable for pdf, doc, ppt, image files):

curl --location --request POST 'https://mineru.net/api/v4/extract/task' \
--header 'Authorization: Bearer ***' \
--header 'Content-Type: application/json' \
--header 'Accept: */*' \
--data-raw '{
    "url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
    "model_version": "vlm"
}'
CURL request example (applicable for html files):

curl --location --request POST 'https://mineru.net/api/v4/extract/task' \
--header 'Authorization: Bearer ***' \
--header 'Content-Type: application/json' \
--header 'Accept: */*' \
--data-raw '{
    "url": "https://****",
    "model_version": "MinerU-HTML"
}'
Request Body Parameter Description

Parameter	Type	Required	Example	Description
url	string	Yes	https://static.openxlab.org.cn/
opendatalab/pdf/demo.pdf	File URL, supports .pdf, .doc, .docx, .ppt, .pptx, images (png/jpg/jpeg/jp2/webp/gif/bmp), .html and other formats
is_ocr	bool	No	false	Whether to enable OCR functionality, default false, only effective for pipeline and vlm models
enable_formula	bool	No	true	Whether to enable formula recognition, default true, only effective for pipeline and vlm models. Special note: for vlm model, this parameter only affects inline formula parsing
enable_table	bool	No	true	Whether to enable table recognition, default true, only effective for pipeline and vlm models
language	string	No	ch	Specify document language, default ch. See language value reference for options. Only effective for pipeline and vlm models
data_id	string	No	abc**	Data ID corresponding to the parsed object. Composed of uppercase and lowercase English letters, numbers, underscores (_), hyphens (-), and periods (.), not exceeding 128 characters, can be used to uniquely identify your business data.
callback	string	No	http://127.0.0.1/callback	URL for parsing result callback notification, supports HTTP and HTTPS protocol addresses. When this field is empty, you must periodically poll for parsing results. The callback endpoint must support POST method, UTF-8 encoding, Content-Type:application/json for data transmission, and parameters checksum and content. The parsing endpoint sets checksum and content according to the following rules and format, calling your callback endpoint to return detection results.
checksum: String format, generated by concatenating user uid + seed + content and applying SHA256 algorithm. User UID can be queried in the personal center. For tamper prevention, you can generate the string using the above algorithm when receiving the push result and verify it against checksum.
content: JSON string format, please parse and convert to JSON object yourself. For content result examples, please refer to the task query result response example, corresponding to the data part of the task query result.
Note: After your server-side callback endpoint receives the result pushed by Mineru parsing service, if the returned HTTP status code is 200, it means successful reception; all other HTTP status codes are considered reception failures. On reception failure, mineru will push the detection result up to 5 times until successful reception. After 5 failed attempts, no more pushes will be made; it is recommended to check the status of your callback endpoint.
seed	string	No	abc**	Random string, used for signature in callback notification requests. Composed of English letters, numbers, and underscores (_), not exceeding 64 characters, defined by you. Used to verify that the request was initiated by Mineru parsing service when receiving content security callback notifications.
Note: When using callback, this field must be provided.
extra_formats	[string]	No	["docx","html"]	markdown and json are default export formats, no need to set. This parameter only supports one or more of docx, html, latex formats. Not effective for source files that are html.
model_version	string	No	vlm	MinerU model version, three options: pipeline, vlm, MinerU-HTML, default pipeline. If parsing HTML files, model_version must be explicitly specified as MinerU-HTML; for non-HTML files, you can choose pipeline or vlm
no_cache	bool	No	false	Whether to bypass cache, default false. Our API server caches URL content for a period; setting to true ignores cached results and fetches the latest content from the URL.
cache_tolerance	int	No	900	Cache tolerance time (seconds), default 900 (15 minutes). The tolerable URL content cache validity period; cache beyond this time will not be used. Effective when no_cache is false
Response Parameter Description

Parameter	Type	Example	Description
code	int	0	Endpoint status code, success: 0
msg	string	ok	Endpoint processing message, success: "ok"
trace_id	string	c876cd60b202f2396de1f9e39a1b0172	Request ID
data.task_id	string	a90e6ab6-44f3-4554-b459-b62fe4c6b436	Extraction task id, can be used to query task results
Response Example

{
  "code": 0,
  "data": {
    "task_id": "a90e6ab6-44f3-4554-b4***"
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
Get Task Results
Endpoint Description

Query the current progress of an extraction task via task_id. After task processing is complete, the endpoint will respond with the corresponding extraction details.

Python Request Example

import requests

token = "API token applied from official website"
task_id = "task_id returned from the previous step"
url = f"https://mineru.net/api/v4/extract/task/{task_id}"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

res = requests.get(url, headers=header)
print(res.status_code)
print(res.json())
print(res.json()["data"])
CURL Request Example

curl --location --request GET 'https://mineru.net/api/v4/extract/task/{task_id}' \
--header 'Authorization: Bearer *****' \
--header 'Accept: */*'
Response Parameter Description

Parameter	Type	Example	Description
code	int	0	Endpoint status code, success: 0
msg	string	ok	Endpoint processing message, success: "ok"
trace_id	string	c876cd60b202f2396de1f9e39a1b0172	Request ID
data.task_id	string	abc**	Task ID
data.data_id	string	abc**	Data ID corresponding to the parsed object.
Note: If data_id was passed in the parsing request parameters, the corresponding data_id is returned here.
data.state	string	done	Task processing status, done: complete, pending: queued, running: parsing in progress, failed: parsing failed, converting: format conversion in progress
data.full_zip_url	string	https://cdn-mineru.openxlab.org.cn/
pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip	File parsing result archive
For detailed description of non-html file parsing results, please refer to: https://opendatalab.github.io/MinerU/reference/output_files/ , where layout.json corresponds to intermediate processing results (middle.json), **_model.json corresponds to model inference results (model.json), **_content_list.json corresponds to content list (content_list.json), full.md is the Markdown parsing result.

html file parsing results are slightly different: full.md is the Markdown parsing result, main.html is the extracted body html
data.err_msg	string	File format not supported, please upload a valid file type	Parsing failure reason, effective when state=failed
data.extract_progress.extracted_pages	int	1	Document parsed pages, effective when state=running
data.extract_progress.start_time	string	2025-01-20 11:43:20	Document parsing start time, effective when state=running
data.extract_progress.total_pages	int	2	Document total pages, effective when state=running
Response Example

{
  "code": 0,
  "data": {
    "task_id": "47726b6e-46ca-4bb9-******",
    "state": "running",
    "err_msg": "",
    "extract_progress": {
      "extracted_pages": 1,
      "total_pages": 2,
      "start_time": "2025-01-20 11:43:20"
    }
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
{
  "code": 0,
  "data": {
    "task_id": "47726b6e-46ca-4bb9-******",
    "state": "done",
    "full_zip_url": "https://cdn-mineru.openxlab.org.cn/pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip",
    "err_msg": ""
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
Batch File Parsing
Local File Batch Upload Parsing
Endpoint Description

Applicable for local file upload parsing scenarios, this endpoint can batch apply for file upload links. After uploading files, the system automatically submits parsing tasks. Note:

The applied file upload links are valid for 24 hours, please complete file upload within the validity period
When uploading files, no need to set the Content-Type header
After file upload is complete, no need to call the submit parsing task endpoint. The system automatically scans uploaded files and submits parsing tasks
A single link application cannot exceed 200 files
The header must include the Authorization field, formatted as Bearer + space + Token
Python request example (applicable for pdf, doc, ppt, image files):

import requests

token = "API token applied from official website"
url = "https://mineru.net/api/v4/file-urls/batch"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "files": [
        {"name":"demo.pdf", "data_id": "abcd"}
    ],
    "model_version":"vlm"
}
file_path = ["demo.pdf"]
try:
    response = requests.post(url,headers=header,json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            print('batch_id:{},urls:{}'.format(batch_id, urls))
            for i in range(0, len(urls)):
                with open(file_path[i], 'rb') as f:
                    res_upload = requests.put(urls[i], data=f)
                    if res_upload.status_code == 200:
                        print(f"{urls[i]} upload success")
                    else:
                        print(f"{urls[i]} upload failed")
        else:
            print('apply upload url failed,reason:{}'.format(result["msg"]))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
except Exception as err:
    print(err)
Python request example (applicable for html files):

import requests

token = "API token applied from official website"
url = "https://mineru.net/api/v4/file-urls/batch"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "files": [
        {"name":"demo.html", "data_id": "abcd"}
    ],
    "model_version":"MinerU-HTML"
}
file_path = ["demo.html"]
try:
    response = requests.post(url,headers=header,json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            print('batch_id:{},urls:{}'.format(batch_id, urls))
            for i in range(0, len(urls)):
                with open(file_path[i], 'rb') as f:
                    res_upload = requests.put(urls[i], data=f)
                    if res_upload.status_code == 200:
                        print(f"{urls[i]} upload success")
                    else:
                        print(f"{urls[i]} upload failed")
        else:
            print('apply upload url failed,reason:{}'.format(result["msg"]))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
except Exception as err:
    print(err)
CURL request example (applicable for pdf, doc, ppt, image files):

curl --location --request POST 'https://mineru.net/api/v4/file-urls/batch' \
--header 'Authorization: Bearer ***' \
--header 'Content-Type: application/json' \
--header 'Accept: */*' \
--data-raw '{
    "files": [
        {"name":"demo.pdf", "data_id": "abcd"}
    ],
    "model_version": "vlm"
}'
CURL request example (applicable for html files):

curl --location --request POST 'https://mineru.net/api/v4/file-urls/batch' \
--header 'Authorization: Bearer ***' \
--header 'Content-Type: application/json' \
--header 'Accept: */*' \
--data-raw '{
    "files": [
        {"name":"demo.html", "data_id": "abcd"}
    ],
    "model_version": "MinerU-HTML"
}'
CURL file upload example:

curl -X PUT -T /path/to/your/file.pdf 'https://****'
Request Body Parameter Description

Parameter	Type	Required	Example	Description
enable_formula	bool	No	true	Whether to enable formula recognition, default true, only effective for pipeline and vlm models. Special note: for vlm model, this parameter only affects inline formula parsing
enable_table	bool	No	true	Whether to enable table recognition, default true, only effective for pipeline and vlm models
language	string	No	ch	Specify document language, default ch. See language value reference for options. Only effective for pipeline and vlm models
file.name	string	Yes	demo.pdf	File name, supports .pdf, .doc, .docx, .ppt, .pptx, images (png/jpg/jpeg/jp2/webp/gif/bmp), .html and other formats. We strongly recommend including the correct file extension
file.is_ocr	bool	No	true	Whether to enable OCR functionality, default false, only effective for pipeline and vlm models
file.data_id	string	No	abc**	Data ID corresponding to the parsed object. Composed of uppercase and lowercase English letters, numbers, underscores (_), hyphens (-), and periods (.), not exceeding 128 characters, can be used to uniquely identify your business data.
file.page_ranges	string	No	1-600	Specify page range, format as comma-separated string. For example: "2,4-6": means select page 2, pages 4 to 6 (including 4 and 6, result is [2,4,5,6]); "2--2": means select from page 2 to the second-to-last page (where "-2" means second-to-last page).
callback	string	No	http://127.0.0.1/callback	URL for parsing result callback notification, supports HTTP and HTTPS protocol addresses. When this field is empty, you must periodically poll for parsing results. The callback endpoint must support POST method, UTF-8 encoding, Content-Type:application/json for data transmission, and parameters checksum and content. The parsing endpoint sets checksum and content according to the following rules and format, calling your callback endpoint to return detection results.
checksum: String format, generated by concatenating user uid + seed + content and applying SHA256 algorithm. User UID can be queried in the personal center. For tamper prevention, you can generate the string using the above algorithm when receiving the push result and verify it against checksum.
content: JSON string format, please parse and convert to JSON object yourself. For content result examples, please refer to the task query result response example, corresponding to the data part of the task query result.
Note: After your server-side callback endpoint receives the result pushed by Mineru parsing service, if the returned HTTP status code is 200, it means successful reception; all other HTTP status codes are considered reception failures. On reception failure, mineru will push the detection result up to 5 times until successful reception. After 5 failed attempts, no more pushes will be made; it is recommended to check the status of your callback endpoint.
seed	string	No	abc**	Random string, used for signature in callback notification requests. Composed of English letters, numbers, and underscores (_), not exceeding 64 characters. Defined by you, used to verify that the request was initiated by Mineru parsing service when receiving content security callback notifications.
Note: When using callback, this field must be provided.
extra_formats	[string]	No	["docx","html"]	markdown and json are default export formats, no need to set. This parameter only supports one or more of docx, html, latex formats. Not effective for source files that are html.
model_version	string	No	vlm	MinerU model version, three options: pipeline, vlm, MinerU-HTML, default pipeline. If parsing HTML files, model_version must be explicitly specified as MinerU-HTML; for non-HTML files, you can choose pipeline or vlm
Response Parameter Description

Parameter	Type	Example	Description
code	int	0	Endpoint status code, success: 0
msg	string	ok	Endpoint processing message, success: "ok"
trace_id	string	c876cd60b202f2396de1f9e39a1b0172	Request ID
data.batch_id	string	2bb2f0ec-a336-4a0a-b61a-****	Batch extraction task id, can be used to batch query parsing results
data.file_urls	string	["https://mineru.oss-cn-shanghai.aliyuncs.com/api-upload/***"]	File upload links
Response Example

{
  "code": 0,
  "data": {
    "batch_id": "2bb2f0ec-a336-4a0a-b61a-241afaf9cc87",
    "file_urls": ["https://***"]
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
URL Batch Upload Parsing
Endpoint Description

Applicable for creating batch extraction tasks via API. Note:

A single link application cannot exceed 200 files
File size cannot exceed 200MB, file pages cannot exceed 600 pages
Due to network limitations, foreign URLs like github, aws may experience request timeouts
The header must include the Authorization field, formatted as Bearer + space + Token
Python request example (applicable for pdf, doc, ppt, image files):

import requests

token = "API token applied from official website"
url = "https://mineru.net/api/v4/extract/task/batch"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "files": [
        {"url":"https://cdn-mineru.openxlab.org.cn/demo/example.pdf", "data_id": "abcd"}
    ],
    "model_version": "vlm"
}
try:
    response = requests.post(url,headers=header,json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            print('batch_id:{}'.format(batch_id))
        else:
            print('submit task failed,reason:{}'.format(result["msg"]))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
except Exception as err:
    print(err)
Python request example (applicable for html files):

import requests

token = "API token applied from official website"
url = "https://mineru.net/api/v4/extract/task/batch"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "files": [
        {"url":"https://***", "data_id": "abcd"}
    ],
    "model_version": "MinerU-HTML"
}
try:
    response = requests.post(url,headers=header,json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            print('batch_id:{}'.format(batch_id))
        else:
            print('submit task failed,reason:{}'.format(result["msg"]))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
except Exception as err:
    print(err)
CURL request example (applicable for pdf, doc, ppt, image files):

curl --location --request POST 'https://mineru.net/api/v4/extract/task/batch' \
--header 'Authorization: Bearer ***' \
--header 'Content-Type: application/json' \
--header 'Accept: */*' \
--data-raw '{
    "files": [
        {"url":"https://cdn-mineru.openxlab.org.cn/demo/example.pdf", "data_id": "abcd"}
    ],
    "model_version": "vlm"
}'
CURL request example (applicable for html files):

curl --location --request POST 'https://mineru.net/api/v4/extract/task/batch' \
--header 'Authorization: Bearer ***' \
--header 'Content-Type: application/json' \
--header 'Accept: */*' \
--data-raw '{
    "files": [
        {"url":"https://***", "data_id": "abcd"}
    ],
    "model_version": "MinerU-HTML"
}'
Request Body Parameter Description

Parameter	Type	Required	Example	Description
enable_formula	bool	No	true	Whether to enable formula recognition, default true, only effective for pipeline and vlm models. Special note: for vlm model, this parameter only affects inline formula parsing
enable_table	bool	No	true	Whether to enable table recognition, default true, only effective for pipeline and vlm models
language	string	No	ch	Specify document language, default ch. See language value reference for options. Only effective for pipeline and vlm models
file.url	string	Yes	demo.pdf	File link, supports .pdf, .doc, .docx, .ppt, .pptx, images (png/jpg/jpeg/jp2/webp/gif/bmp), .html and other formats
file.is_ocr	bool	No	true	Whether to enable OCR functionality, default false, only effective for pipeline and vlm models
file.data_id	string	No	abc**	Data ID corresponding to the parsed object. Composed of uppercase and lowercase English letters, numbers, underscores (_), hyphens (-), and periods (.), not exceeding 128 characters, can be used to uniquely identify your business data.
file.page_ranges	string	No	1-600	Specify page range, format as comma-separated string. For example: "2,4-6": means select page 2, pages 4 to 6 (including 4 and 6, result is [2,4,5,6]); "2--2": means select from page 2 to the second-to-last page (where "-2" means second-to-last page).
callback	string	No	http://127.0.0.1/callback	URL for parsing result callback notification, supports HTTP and HTTPS protocol addresses. When this field is empty, you must periodically poll for parsing results. The callback endpoint must support POST method, UTF-8 encoding, Content-Type:application/json for data transmission, and parameters checksum and content. The parsing endpoint sets checksum and content according to the following rules and format, calling your callback endpoint to return detection results.
checksum: String format, generated by concatenating user uid + seed + content and applying SHA256 algorithm. User UID can be queried in the personal center. For tamper prevention, you can generate the string using the above algorithm when receiving the push result and verify it against checksum.
content: JSON string format, please parse and convert to JSON object yourself. For content result examples, please refer to the task query result response example, corresponding to the data part of the task query result.
Note: After your server-side callback endpoint receives the result pushed by Mineru parsing service, if the returned HTTP status code is 200, it means successful reception; all other HTTP status codes are considered reception failures. On reception failure, mineru will push the detection result up to 5 times until successful reception. After 5 failed attempts, no more pushes will be made; it is recommended to check the status of your callback endpoint.
seed	string	No	abc**	Random string, used for signature in callback notification requests. Composed of English letters, numbers, and underscores (_), not exceeding 64 characters. Defined by you, used to verify that the request was initiated by Mineru parsing service when receiving content security callback notifications.
Note: When using callback, this field must be provided.
extra_formats	[string]	No	["docx","html"]	markdown and json are default export formats, no need to set. This parameter only supports one or more of docx, html, latex formats. Not effective for source files that are html.
model_version	string	No	vlm	MinerU model version, three options: pipeline, vlm, MinerU-HTML, default pipeline. If parsing HTML files, model_version must be explicitly specified as MinerU-HTML; for non-HTML files, you can choose pipeline or vlm
no_cache	bool	No	false	Whether to bypass cache, default false. Our API server caches URL content for a period; setting to true ignores cached results and fetches the latest content from the URL.
cache_tolerance	int	No	900	Cache tolerance time (seconds), default 900 (15 minutes). The tolerable URL content cache validity period; cache beyond this time will not be used. Effective when no_cache is false
Request Body Example

{
  "files": [
    {
      "url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
      "data_id": "abcd"
    }
  ],
  "model_version": "vlm"
}
Response Parameter Description

Parameter	Type	Example	Description
code	int	0	Endpoint status code, success: 0
msg	string	ok	Endpoint processing message, success: "ok"
trace_id	string	c876cd60b202f2396de1f9e39a1b0172	Request ID
data.batch_id	string	2bb2f0ec-a336-4a0a-b61a-****	Batch extraction task id, can be used to batch query parsing results
Response Example

{
  "code": 0,
  "data": {
    "batch_id": "2bb2f0ec-a336-4a0a-b61a-241afaf9cc87"
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
Batch Get Task Results
Endpoint Description

Batch query the progress of extraction tasks via batch_id.

Python Request Example

import requests

token = "API token applied from official website"
batch_id = "batch_id returned from the previous batch submission"
url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

res = requests.get(url, headers=header)
print(res.status_code)
print(res.json())
print(res.json()["data"])
CURL Request Example

curl --location --request GET 'https://mineru.net/api/v4/extract-results/batch/{batch_id}' \
--header 'Authorization: Bearer *****' \
--header 'Accept: */*'
Response Parameter Description

Parameter	Type	Example	Description
code	int	0	Endpoint status code, success: 0
msg	string	ok	Endpoint processing message, success: "ok"
trace_id	string	c876cd60b202f2396de1f9e39a1b0172	Request ID
data.batch_id	string	2bb2f0ec-a336-4a0a-b61a-241afaf9cc87	batch_id
data.extract_result.file_name	string	demo.pdf	File name
data.extract_result.state	string	done	Task processing status, done: complete, waiting-file: waiting for file upload to queue and submit parsing task, pending: queued, running: parsing in progress, failed: parsing failed, converting: format conversion in progress
data.extract_result.full_zip_url	string	https://cdn-mineru.openxlab.org.cn/pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip	File parsing result archive
For detailed description of non-html file parsing results, please refer to: https://opendatalab.github.io/MinerU/reference/output_files/ , where layout.json corresponds to intermediate processing results (middle.json), **_model.json corresponds to model inference results (model.json), **_content_list.json corresponds to content list (content_list.json), full.md is the Markdown parsing result.

html file parsing results are slightly different: full.md is the Markdown parsing result, main.html is the extracted body html
data.extract_result.err_msg	string	File format not supported, please upload a valid file type	Parsing failure reason, effective when state=failed
data.extract_result.data_id	string	abc**	Data ID corresponding to the parsed object.
Note: If data_id was passed in the parsing request parameters, the corresponding data_id is returned here.
data.extract_result.extract_progress.extracted_pages	int	1	Document parsed pages, effective when state=running
data.extract_result.extract_progress.start_time	string	2025-01-20 11:43:20	Document parsing start time, effective when state=running
data.extract_result.extract_progress.total_pages	int	2	Document total pages, effective when state=running
Response Example

{
  "code": 0,
  "data": {
    "batch_id": "2bb2f0ec-a336-4a0a-b61a-241afaf9cc87",
    "extract_result": [
      {
        "file_name": "example.pdf",
        "state": "done",
        "err_msg": "",
        "full_zip_url": "https://cdn-mineru.openxlab.org.cn/pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip"
      },
      {
        "file_name": "demo.pdf",
        "state": "running",
        "err_msg": "",
        "extract_progress": {
          "extracted_pages": 1,
          "total_pages": 2,
          "start_time": "2025-01-20 11:43:20"
        }
      }
    ]
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
Common Error Codes
Error Code	Description	Suggested Solution
A0202	Token Error	Check if the token is correct, verify if Bearer prefix is present, or replace with a new token
A0211	Token Expired	Replace with a new token
-500	Parameter Error	Ensure parameter types and Content-Type are correct
-10001	Service Exception	Please try again later
-10002	Request Parameter Error	Check request parameter format
-60001	Failed to generate upload URL, please try again later	Please try again later
-60002	Failed to get matching file format	File type detection failed; ensure the requested file name and link have correct extensions, and the file is one of pdf, doc, docx, ppt, pptx, png, jp(e)g
-60003	File Read Failed	Please check if the file is corrupted and re-upload
-60004	Empty File	Please upload a valid file
-60005	File Size Exceeds Limit	Check file size, maximum supported is 200MB
-60006	File Page Count Exceeds Limit	Please split the file and retry
-60007	Model Service Temporarily Unavailable	Please retry later or contact technical support
-60008	File Read Timeout	Check if URL is accessible
-60009	Task Submission Queue Full	Please try again later
-60010	Parsing Failed	Please try again later
-60011	Failed to Get Valid File	Please ensure the file has been uploaded
-60012	Task Not Found	Please ensure the task_id is valid and not deleted
-60013	No Permission to Access Task	You can only access tasks you submitted
-60014	Delete Running Task	Running tasks do not support deletion
-60015	File Conversion Failed	You can manually convert to PDF and re-upload
-60016	File Conversion Failed	File conversion to specified format failed; try exporting in another format or retry
-60017	Retry Limit Reached	Retry after subsequent model upgrades
-60018	Daily Parsing Task Limit Reached	Come back tomorrow
-60019	HTML File Parsing Quota Insufficient	Come back tomorrow
-60020	File Split Failed	Please retry later
-60021	Failed to Read File Page Count	Please retry later
-60022	Webpage Read Failed	May be due to network issues or rate limiting causing read failure; please retry later
