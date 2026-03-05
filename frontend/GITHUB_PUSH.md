# رفع المشروع على GitHub

## ✅ المشروع جاهز! الآن تحتاجين للمصادقة:

### الطريقة 1: استخدام Personal Access Token (الأسهل)

1. اذهبي إلى: https://github.com/settings/tokens
2. اضغطي "Generate new token" → "Generate new token (classic)"
3. أعطي الـ token اسم (مثل: `raboo3-push`)
4. اختر الصلاحيات: ✅ `repo` (كل الصلاحيات)
5. اضغطي "Generate token"
6. **انسخي الـ token** (لن يظهر مرة أخرى!)

7. ثم شغلي:
```bash
cd /Users/sarah/Roboo3/raboo3-frontend
git push -u origin main
```

8. عندما يطلب منك:
   - Username: `SarahO10`
   - Password: **الصق الـ token هنا** (ليس كلمة المرور!)

---

### الطريقة 2: استخدام GitHub CLI

```bash
gh auth login
# اتبعي التعليمات على الشاشة
git push -u origin main
```

---

### الطريقة 3: استخدام SSH (إذا كان لديك SSH key)

```bash
git remote set-url origin git@github.com:SarahO10/raboo3-frontend.git
git push -u origin main
```

---

**الطريقة الأسهل:** Personal Access Token! 🚀

