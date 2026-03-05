#!/bin/bash
# سكريبت سريع لرفع المشروع على GitHub

echo "🚀 رفع المشروع على GitHub..."

# استبدلي YOUR_USERNAME باسم المستخدم في GitHub
USERNAME="YOUR_USERNAME"
REPO_NAME="raboo3-frontend"

# إضافة remote
git remote add origin https://github.com/${USERNAME}/${REPO_NAME}.git 2>/dev/null || git remote set-url origin https://github.com/${USERNAME}/${REPO_NAME}.git

# رفع الكود
git push -u origin main

echo "✅ تم الرفع بنجاح!"
echo "🌐 Repository: https://github.com/${USERNAME}/${REPO_NAME}"

