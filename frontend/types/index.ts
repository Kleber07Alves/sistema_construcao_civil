// frontend/types/index.ts
// ─────────────────────────────────────────────────────────────────────────────
// Fonte única de tipos TypeScript compartilhados pelo frontend.
// ─────────────────────────────────────────────────────────────────────────────

// =============================================================================
// Autenticação e controle de acesso
// =============================================================================

/** Perfis espelhados do backend (models.py → PerfilUsuario). */
export type PerfilUsuario = "gestor" | "operador" | "rh";

/** Dados do usuário mantidos em memória após o login. */
export interface UsuarioLogado {
  nome: string;
  perfil: PerfilUsuario;
}

/** Payload da resposta de POST /auth/login. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  perfil: PerfilUsuario;
  nome: string;
}

// =============================================================================
// Core — Obras e Usuários
// =============================================================================

export type StatusObra    = "planejada" | "em_andamento" | "concluida" | "pausada";
export type PrioridadeObra = "alta" | "media" | "baixa";

export interface Obra {
  id: number;
  nome: string;
  endereco: string;
  status: StatusObra;
  prioridade: PrioridadeObra;
  data_inicio: string | null;
}

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  perfil: PerfilUsuario;
  ativo: boolean;
}

// =============================================================================
// Módulo Logístico
// =============================================================================

export type StatusPedido = "pendente" | "entregue" | "atrasado";
export type NivelAlerta  = "vermelho" | "amarelo" | "verde";

export interface Fornecedor {
  id: number;
  nome: string;
  contato: string;
  media_atraso_dias: number;
  taxa_atraso: number;
  total_pedidos: number;
  desvio_atraso_dias: number;
  observacao: string | null;
}

export interface Pedido {
  id: number;
  data_pedido: string;
  data_prevista: string;
  data_real_entrega: string | null;
  tipo_insumo: string;
  fornecedor_id: number;
  obra_id: number;
  prioridade: PrioridadeObra;
  status: StatusPedido;
  prob_atraso: number;
  nivel_alerta: NivelAlerta;
  texto_alerta: string;
  observacao: string | null;
}

export interface Alerta {
  pedido_id: number;
  obra: string;
  fornecedor: string;
  tipo_insumo: string;
  prioridade: PrioridadeObra;
  data_prevista: string;
  prob_atraso: number;
  nivel_alerta: NivelAlerta;
  texto_alerta: string;
}

export interface DashboardLogistico {
  total_pedidos_ativos: number;
  alertas_vermelhos: number;
  alertas_amarelos: number;
  alertas_verdes: number;
  alertas: Alerta[];
  fornecedores: Fornecedor[];
}

// =============================================================================
// Módulo de RH
// =============================================================================

export type StatusVaga = "aberta" | "pausada" | "encerrada";

export interface Vaga {
  id: number;
  titulo: string;
  tipo_obra: string;
  requisitos: string;
  habilidades: string;
  status: StatusVaga;
}

export interface Candidato {
  id: number;
  nome: string;
  email: string;
  cargo: string;
  experiencia_anos: number;
  habilidades: string;
  curriculo_texto: string | null;
  resumo: string | null;
}

export interface RankingCandidato {
  candidato: Candidato;
  score: number;
  motivos: string[];
}