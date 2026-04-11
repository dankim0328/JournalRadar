/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: false, // GitHub Pages와 더 잘 맞음
  basePath: '/JournalRadar',
  assetPrefix: '/JournalRadar', // 에셋 경로 명시적 지정
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
