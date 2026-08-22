/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    AUDIT_SERVICE_URL: process.env.AUDIT_SERVICE_URL || 'http://localhost:3003',
  },
}

module.exports = nextConfig
