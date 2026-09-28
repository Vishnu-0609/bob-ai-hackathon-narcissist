/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['127.0.0.1'],
  devIndicators: false,
  async rewrites() {
    return [{ source: '/backend/:path*', destination: `${process.env.BACKEND_URL || 'http://127.0.0.1:4000'}/:path*` }]
  },
}

export default nextConfig
