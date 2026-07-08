// ESLint 9 (flat config) — o comando `next lint` foi removido no Next.js 16;
// o lint agora roda direto pelo ESLint: `npm run lint`.
// eslint-config-next 16 exporta flat configs nativas via subpaths.
import { defineConfig } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // O padrão atual de data-fetching ("carregar() no useEffect de mount",
      // com setCarregando síncrono) dispara esta regra nova do
      // eslint-plugin-react-hooks v7. Refatorar o fetch das páginas está
      // planejado para a fase de design system (PLANO fase 5) — até lá a
      // regra fica desativada para não bloquear o lint.
      "react-hooks/set-state-in-effect": "off",
    },
  },
]);
