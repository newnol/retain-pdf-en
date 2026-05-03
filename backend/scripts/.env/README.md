# Local Keys

This directory only stores key files used during local development.

Current convention:

- `mineru.env`
  Write `MINERU_API_TOKEN=...` in the file

Notes:

- The actual `*.env` files in this directory have been Git-ignored
- This is only for local development, not for external delivery
- If `--token` is passed on the command line, the command line argument takes precedence
