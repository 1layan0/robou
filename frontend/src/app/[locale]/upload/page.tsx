'use client';

import { useState, useCallback } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';
import { motion } from 'framer-motion';
import { useI18n, useT } from '@/i18n/useTranslations';

interface UploadFile {
  file: File;
  type: 'transactions' | 'facilities' | 'districts' | 'prices';
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
}

export default function UploadPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [uploadType, setUploadType] = useState<'transactions' | 'facilities' | 'districts' | 'prices'>('transactions');
  const [dragging, setDragging] = useState(false);

  const handleFileSelect = useCallback(
    (selectedFiles: FileList | null) => {
      if (!selectedFiles || selectedFiles.length === 0) return;

      const newFiles: UploadFile[] = Array.from(selectedFiles).map((file) => ({
        file,
        type: uploadType,
        progress: 0,
        status: 'pending' as const,
      }));

      setFiles((prev) => [...prev, ...newFiles]);
      addNotification({
        type: 'info',
        title: isAr ? 'تم إضافة الملفات' : 'Files Added',
        message: isAr ? `تم إضافة ${newFiles.length} ملف للرفع` : `${newFiles.length} file(s) added for upload`,
        duration: 3000,
      });
    },
    [uploadType, addNotification]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      handleFileSelect(e.dataTransfer.files);
    },
    [handleFileSelect]
  );

  const handleUpload = useCallback(
    async (fileItem: UploadFile) => {
      const fileIndex = files.findIndex((f) => f.file === fileItem.file);
      setFiles((prev) => {
        const updated = [...prev];
        updated[fileIndex] = { ...updated[fileIndex], status: 'uploading' };
        return updated;
      });

      // Mock upload - replace with actual API call
      const interval = setInterval(() => {
        setFiles((prev) => {
          const updated = [...prev];
          const current = updated[fileIndex];
          if (current.progress < 100) {
            updated[fileIndex] = { ...current, progress: current.progress + 10 };
            return updated;
          }
          clearInterval(interval);
          updated[fileIndex] = { ...current, status: 'success' };
          addNotification({
            type: 'success',
            title: isAr ? 'تم الرفع بنجاح' : 'Upload Successful',
            message: isAr ? `تم رفع ${current.file.name} بنجاح` : `${current.file.name} uploaded successfully`,
            duration: 3000,
          });
          return updated;
        });
      }, 200);
    },
    [files, addNotification]
  );

  const handleRemove = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleUploadAll = useCallback(() => {
    files.filter((f) => f.status === 'pending').forEach(handleUpload);
  }, [files, handleUpload]);

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-4xl space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.upload.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.upload.subtitle}
          </p>
        </header>

        <div className="card p-6 space-y-6">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-ink-900 dark:text-white">
              {t.upload.data_type}
            </label>
            <select
              value={uploadType}
              onChange={(e) => setUploadType(e.target.value as 'transactions' | 'facilities' | 'districts' | 'prices')}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
            >
              <option value="transactions">{t.upload.data_type_transactions}</option>
              <option value="facilities">{t.upload.data_type_facilities}</option>
              <option value="districts">{t.upload.data_type_districts}</option>
              <option value="prices">{t.upload.data_type_prices}</option>
            </select>
          </div>

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
              dragging
                ? 'border-raboo3-400 bg-raboo3-50 dark:bg-raboo3-900/10'
                : 'border-slate-300 dark:border-slate-700'
            }`}
          >
            <input
              type="file"
              multiple
              accept=".csv,.json,.xlsx,.xls"
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer flex flex-col items-center gap-4"
            >
              <div className="w-16 h-16 rounded-full bg-raboo3-100 dark:bg-raboo3-900/30 flex items-center justify-center">
                <span className="text-3xl">📁</span>
              </div>
              <div>
                <div className="text-lg font-semibold text-ink-900 dark:text-white">
                  {t.upload.drag_drop}
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  {t.upload.file_formats}
                </div>
              </div>
            </label>
          </div>

          {files.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-ink-900 dark:text-white">
                  {t.upload.files_added.replace('{count}', files.length.toString())}
                </h3>
                <button onClick={handleUploadAll} className="btn btn-primary text-sm">
                  {t.upload.upload_all}
                </button>
              </div>

              <div className="space-y-3">
                {files.map((fileItem, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 dark:bg-ink-900/50"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-ink-900 dark:text-white truncate">
                        {fileItem.file.name}
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400">
                        {(fileItem.file.size / 1024).toFixed(2)} KB
                      </div>
                      {fileItem.status === 'uploading' && (
                        <div className="mt-2">
                          <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-raboo3-600 transition-all duration-300"
                              style={{ width: `${fileItem.progress}%` }}
                            />
                          </div>
                          <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                            {fileItem.progress}% - {t.upload.uploading}
                          </div>
                        </div>
                      )}
                      {fileItem.status === 'success' && (
                        <div className="text-xs text-green-600 dark:text-green-400 mt-1">
                          {t.upload.uploaded}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {fileItem.status === 'pending' && (
                        <button
                          onClick={() => handleUpload(fileItem)}
                          className="btn btn-primary text-sm px-4 py-2"
                        >
                          {t.upload.upload}
                        </button>
                      )}
                      <button
                        onClick={() => handleRemove(index)}
                        className="btn border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 text-sm px-4 py-2 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
                      >
                        {t.upload.delete}
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="card p-6 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800">
          <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">{t.upload.important_info}</h3>
          <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
            <li>{t.upload.info_item1}</li>
            <li>{t.upload.info_item2}</li>
            <li>{t.upload.info_item3}</li>
            <li>{t.upload.info_item4}</li>
          </ul>
        </div>
      </div>
    </main>
  );
}

