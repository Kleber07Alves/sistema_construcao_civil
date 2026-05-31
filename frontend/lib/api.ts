export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  perfil: string;
  nome: string;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function getUsuario(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("usuario") || "";
}

export function logout(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("usuario");
  localStorage.removeItem("perfil");
}

async function tratarResposta<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detalhe = "Erro na API.";
    try {
      const body = await res.json();
      detalhe = body.detail || JSON.stringify(body);
    } catch {
      detalhe = await res.text();
    }
    throw new Error(detalhe || `Erro HTTP ${res.status}.`);
  }
  return res.json();
}

export async function loginDemo(): Promise<LoginResponse> {
  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "gestor@empresa.com", senha: "123456" }),
    });
    const data = await tratarResposta<LoginResponse>(res);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("usuario", data.nome);
    localStorage.setItem("perfil", data.perfil);
    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`Não foi possível conectar ao backend em ${API_URL}. Verifique se o Docker está rodando e se o serviço backend está ativo.`);
    }
    throw error;
  }
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  try {
    const res = await fetch(`${API_URL}${path}`, { ...options, headers });
    return await tratarResposta<T>(res);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`Não foi possível conectar ao backend em ${API_URL}. Verifique se o Docker está rodando e se o serviço backend está ativo.`);
    }
    throw error;
  }
}
