/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['mapbox-gl'],
  // نتجاهل مرحلة ESLint أثناء build في Vercel
  // (تقدرين تشغلين lint محلياً عن طريق: npm run lint)
  eslint: {
    ignoreDuringBuilds: true,
  },
};
export default nextConfig;
