/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * output: 'standalone' gera uma pasta .next/standalone com apenas os
   * arquivos necessários para rodar em produção (sem node_modules completo).
   * Isso reduz a imagem Docker final de ~800 MB para ~200 MB.
   *
   * O frontend/Dockerfile multi-stage copia dessa pasta para a imagem final.
   * Mais: https://nextjs.org/docs/app/api-reference/next-config-js/output
   */
  output: "standalone",
};

export default nextConfig;
