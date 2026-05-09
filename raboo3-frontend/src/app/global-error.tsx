'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <main style={{ padding: '2rem', fontFamily: 'system-ui', maxWidth: '600px', margin: '0 auto' }}>
          <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>حدث خطأ</h1>
          <p style={{ color: '#666', marginBottom: '1rem' }}>{error?.message || 'خطأ غير متوقع'}</p>
          <button
            type="button"
            onClick={() => reset()}
            style={{
              padding: '0.5rem 1rem',
              background: '#0d9488',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            إعادة المحاولة
          </button>
        </main>
      </body>
    </html>
  );
}
