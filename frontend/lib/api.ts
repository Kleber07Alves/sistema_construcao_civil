
// ─────────────────────────────────────────────────────────────────────────────
// Cliente HTTP para o backend FastAPI.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  
const LS_TOKEN   = "token";
const LS_NOME    = "usuario";
const LS_PERFIL  = "perfil";
const COOKIE_KEY = "auth_token";

// =============================================================================
// Leitura do token (usado internamente por apiJson)
// =============================================================================

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(LS_TOKEN);
}

/** @deprecated Use useAuth().usuario em client components. */
export function getUsuario(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(LS_NOME) ?? "";
}

// =============================================================================
// Logout utilitário (chamado pelo AuthContext e pelo interceptor 401)
// =============================================================================

/**
 * Limpa todos os dados de autenticação do browser.
 *
 * Chamado por:
 *   • AuthContext.logout() — via botão "Sair" na NavHeader
 *   • apiJson() — interceptor 401 (token expirado mid-session)
 *
 * Nota: não redireciona — quem redireciona é o AuthContext (tem acesso ao
 * router do Next.js). O interceptor 401 em apiJson faz o redirect diretamente
 * via window.location quando o contexto não está disponível.
 */
export function logout(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(LS_TOKEN);
  localStorage.removeItem(LS_NOME);
  localStorage.removeItem(LS_PERFIL);
  // Expira o cookie lido pelo middleware.ts
  document.cookie = `${COOKIE_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

// =============================================================================
// Tratamento de resposta HTTP
// =============================================================================

async function tratarResposta<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    // No Content — retorna undefined compatível com o tipo T
    return undefined as unknown as T;
  }

  if (!res.ok) {
    // ── Interceptor 401: token expirado ou inválido ───────────────────
    // Limpa o estado de auth e redireciona para /login sem depender do
    // router do Next.js (este módulo é agnóstico ao framework de rotas).
    if (res.status === 401) {
      logout();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Sessão expirada. Faça login novamente.");
    }

    let detalhe = `Erro HTTP ${res.status}.`;
    try {
      const body = await res.json() as { detail?: string };
      detalhe = body.detail ?? JSON.stringify(body);
    } catch {
      detalhe = await res.text();
    }
    throw new Error(detalhe);
  }

  return res.json() as Promise<T>;
}

// =============================================================================
// Cliente HTTP autenticado
// =============================================================================

/**
 * Faz uma requisição autenticada ao backend.
 *
 * Injeta automaticamente o Bearer token do localStorage.
 * Para FormData (upload de arquivo), não define Content-Type para que o
 * browser adicione o boundary correto do multipart.
 *
 * @example
 * const obras = await apiJson<Obra[]>("/core/obras");
 * await apiJson("/core/obras/1", { method: "DELETE" });
 */
export async function apiJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token   = getToken();
  const headers = new Headers(options.headers ?? {});

  // Não sobrescrever Content-Type para FormData (upload de arquivos)
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  try {
    const res = await fetch(`${API_URL}${path}`, { ...options, headers });
    return await tratarResposta<T>(res);
  } catch (error) {
    // Erro de rede (Docker não está rodando, backend caído, etc.)
    if (error instanceof TypeError) {
      throw new Error(
        `Não foi possível conectar ao backend em ${API_URL}. ` +
        "Verifique se o Docker está rodando e o serviço backend está ativo.",
      );
    }
    throw error;
  }
}