/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * output: 'standalone' é para deploys Docker (imagem auto-contida, ~200 MB).
   * No Vercel esta opção NÃO deve ser usada — o Vercel tem seu próprio
   * sistema de otimização e output. Usar standalone no Vercel quebra o build.
   *
   * Solução: ativa standalone APENAS quando a variável DOCKER_BUILD=true
   * está presente (definida no frontend/Dockerfile antes de npm run build).
   * No Vercel essa variável não existe → output fica undefined → comportamento
   * padrão correto do Vercel.
   */
  ...(process.env.DOCKER_BUILD === "true" && { output: "standalone" }),
};

export default nextConfig;
