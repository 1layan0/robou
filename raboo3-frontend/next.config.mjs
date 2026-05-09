/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['mapbox-gl'],
  eslint: {
    ignoreDuringBuilds: true,
  },
  async redirects() {
    return [{ source: '/', destination: '/ar', permanent: false }];
  },
};
export default nextConfig;
