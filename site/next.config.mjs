/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: '/JournalRadar',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
