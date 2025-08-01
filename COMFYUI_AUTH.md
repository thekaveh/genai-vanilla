# ComfyUI Authentication

The ComfyUI service in this stack uses the `ai-dock` Docker image which includes authentication by default.

## Default Credentials

When accessing ComfyUI through:
- Direct URL: `http://localhost:55684/`
- Kong Gateway: `http://localhost:55668/comfyui/`

You will be redirected to a login page. Use these credentials:

- **Username**: `user`
- **Password**: `password`

## Disabling Authentication (Optional)

If you want to disable authentication, you can add these environment variables to the ComfyUI service in the compose profiles:

```yaml
environment:
  - WEB_ENABLE_AUTH=false
  - ENABLE_QUICKTUNNEL=false
```

Note: The exact environment variables may vary depending on the ai-dock image version. Check the image documentation for the most up-to-date configuration options.

## Alternative Solutions

1. Use a different ComfyUI image without authentication
2. Configure a reverse proxy to bypass the authentication layer
3. Use the ComfyUI API directly (bypassing the web UI)