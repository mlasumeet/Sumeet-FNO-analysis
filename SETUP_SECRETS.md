# GitHub Secrets Setup Guide

## For GDRIVE_CREDENTIALS Secret

Your base64 encoded JSON key is ready. Follow these steps on any browser:

1. Go to: https://github.com/mlasumeet/Sumeet-FNO-analysis/settings/secrets/actions
2. Click "New repository secret"
3. Name: `GDRIVE_CREDENTIALS`
4. Value: Copy the content from the file `GDRIVE_CREDENTIALS_BASE64.txt` in this repo
5. Click "Add secret"

## For GDRIVE_FOLDER_ID Secret

1. Go to: https://github.com/mlasumeet/Sumeet-FNO-analysis/settings/secrets/actions
2. Click "New repository secret"
3. Name: `GDRIVE_FOLDER_ID`
4. Value: `1cGJ3GomWi_ueTuj-xiNhIsiLXX4XeVLn`
5. Click "Add secret"

After adding both secrets, delete this file and the GDRIVE_CREDENTIALS_BASE64.txt file for security.
