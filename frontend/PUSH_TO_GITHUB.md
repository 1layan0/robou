# تعليمات رفع المشروع على GitHub

## الخطوات:

### 1. إنشاء Repository على GitHub:
- اذهبي إلى: https://github.com/new
- اسم الـ repository: `raboo3-frontend`
- اختر Public أو Private
- **لا تضيفي** README أو .gitignore (موجودة بالفعل)
- اضغطي "Create repository"

### 2. بعد إنشاء الـ Repository، شغلي الأوامر التالية:

```bash
# إضافة remote (استبدلي YOUR_USERNAME باسم المستخدم)
git remote add origin https://github.com/YOUR_USERNAME/raboo3-frontend.git

# رفع الكود
git push -u origin main
```

### أو إذا كنت تفضلين استخدام SSH:

```bash
git remote add origin git@github.com:YOUR_USERNAME/raboo3-frontend.git
git push -u origin main
```

### 3. إذا واجهت مشكلة في الرفع:

```bash
# إذا كان الـ branch اسمه master بدلاً من main
git branch -M main

# ثم ارفعي مرة أخرى
git push -u origin main
```

---

**ملاحظة:** المشروع جاهز ومُعد للرفع! تم عمل commit لجميع التغييرات.

