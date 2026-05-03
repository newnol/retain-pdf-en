# Prompt Files

This directory stores editable prompt templates used by the main pipeline.

- `translation_system.txt`
  System prompt used for translation requests.
- `translation_task.txt`
  Task description concatenated into the translation user payload.
- `classification_system.txt`
  System prompt used for whole-page classification in `precise` mode.

If you want to adjust model behavior, modify these files first; do not hardcode prompts into Python.
