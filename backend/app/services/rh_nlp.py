# backend/app/services/rh_nlp.py
"""
Serviço de NLP para processamento de currículos.

Pipeline por candidato:
  1. extrair_texto_pdf()  — PyMuPDF → texto bruto (chamado no router)
  2. processar_curriculo()— extração de cargo, experiência, habilidades + resumo
  3. calcular_score()     — compatibilidade candidato × vaga (para ranking)

Estratégia de NLP:
  • spaCy pt_core_news_sm carregado como singleton na primeira chamada
  • Extração usa keyword matching com stem de 6 chars para capturar variações
    morfológicas do PT: "equipes"→"equip"→match "gestão de equipe"
  • Fallback transparente para spacy.blank ou puro regex se o modelo não estiver
    instalado — a aplicação nunca quebra por causa do NLP
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import fitz

logger = logging.getLogger(__name__)

# =============================================================================
# Vocabulários do domínio
# =============================================================================

HABILIDADES_BASE: list[str] = [
    "alvenaria",
    "concreto",
    "elétrica",
    "eletrica",
    "hidráulica",
    "hidraulica",
    "pintura",
    "acabamento",
    "revestimento",
    "drywall",
    "segurança do trabalho",
    "seguranca do trabalho",
    "leitura de projetos",
    "mestre de obras",
    "pedreiro",
    "servente",
    "encanador",
    "eletricista",
    "carpinteiro",
    "operador de máquinas",
    "operador de maquinas",
    "gestão de equipe",
    "gestao de equipe",
    "topografia",
    "impermeabilização",
    "impermeabilizacao",
    "soldagem",
    "concreto armado",
    "NR-35",
    "nr-35",
    "trabalho em altura",
    "argamassa",
    "cerâmica",
    "ceramica",
]

CARGOS_BASE: list[str] = [
    "mestre de obras",
    "pedreiro",
    "servente",
    "encanador",
    "eletricista",
    "carpinteiro",
    "pintor",
    "engenheiro civil",
    "técnico em edificações",
    "tecnico em edificacoes",
    "operador de máquinas",
    "operador de maquinas",
    "arquiteto",
    "topógrafo",
    "topografo",
    "soldador",
    "armador",
    "gesseiro",
]

_NORMALIZACOES: dict[str, str] = {
    "eletrica":                "elétrica",
    "hidraulica":              "hidráulica",
    "seguranca do trabalho":   "segurança do trabalho",
    "gestao de equipe":        "gestão de equipe",
    "operador de maquinas":    "operador de máquinas",
    "tecnico em edificacoes":  "técnico em edificações",
    "topografo":               "topógrafo",
    "impermeabilizacao":       "impermeabilização",
    "ceramica":                "cerâmica",
    "nr-35":                   "NR-35",
}


def _normalizar(texto: str) -> str:
    return _NORMALIZACOES.get(texto.lower(), texto.lower())


# =============================================================================
# Singleton do modelo spaCy
# =============================================================================

_NLP: Any = None          # instância carregada uma única vez
_NLP_INICIALIZADO = False  # flag para não tentar recarregar após falha


def _get_nlp() -> Any:
    """
    Retorna o modelo spaCy, carregando-o na primeira chamada (lazy singleton).

    Tentativas (em ordem):
      1. pt_core_news_sm — lemmatização e NER completos
      2. spacy.blank("pt") — apenas tokenização
      3. None              — sem spaCy; extração por regex puro

    O singleton evita recarregar o modelo a cada chamada (crítico no seed,
    onde processar_curriculo é chamado 3× em sequência).
    """
    global _NLP, _NLP_INICIALIZADO
    if _NLP_INICIALIZADO:
        return _NLP

    _NLP_INICIALIZADO = True
    try:
        import spacy
        try:
            _NLP = spacy.load("pt_core_news_sm")
            logger.info("NLP: pt_core_news_sm carregado.")
        except OSError:
            _NLP = spacy.blank("pt")
            logger.warning("NLP: pt_core_news_sm não encontrado — usando blank('pt').")
    except ImportError:
        _NLP = None
        logger.warning("NLP: spaCy não instalado — extração apenas por regex.")

    return _NLP


# =============================================================================
# Dataclass de resultado
# =============================================================================

@dataclass
class DadosCurriculo:
    texto:            str
    cargo:            str | None
    experiencia_anos: float
    habilidades:      list[str] = field(default_factory=list)
    resumo:           str = ""


# =============================================================================
# Extração de texto do PDF
# =============================================================================

def extrair_texto_pdf(conteudo: bytes) -> str:
    """Extrai texto selecionável de um PDF em memória via PyMuPDF."""
    try:
        with fitz.open(stream=conteudo, filetype="pdf") as doc:
            paginas = [pagina.get_text() for pagina in doc]
        return "\n".join(paginas).strip()
    except Exception as exc:
        logger.error("Erro ao extrair texto do PDF: %s", exc)
        return ""


# =============================================================================
# Extração de cargo
# =============================================================================

def _extrair_cargo_spacy(doc: Any, texto: str) -> str | None:
    """
    Prioriza as 3 primeiras sentenças (cabeçalho do CV) para encontrar o cargo.
    Usa entidades MISC como segundo recurso.
    """
    # a) Foco no cabeçalho: primeiras 3 sentenças
    header = ""
    for i, sent in enumerate(doc.sents):
        if i >= 3:
            break
        header += sent.text.lower() + " "

    for cargo in CARGOS_BASE:
        if cargo.lower() in header:
            return _normalizar(cargo)

    # b) Entidades MISC/PER do NER
    for ent in doc.ents:
        if ent.label_ in ("MISC", "PER"):
            for cargo in CARGOS_BASE:
                if cargo.lower() in ent.text.lower():
                    return _normalizar(cargo)

    return None


def _extrair_cargo_regex(texto: str) -> str | None:
    """Fallback por keyword e padrão 'Cargo: ...'."""
    texto_min = texto.lower()
    for cargo in CARGOS_BASE:
        if cargo.lower() in texto_min:
            return _normalizar(cargo)

    m = re.search(
        r"(?:cargo|função|funcao|vaga|objetivo)\s*[:\-]\s*([A-Za-zÀ-ÿ\s]{3,80})",
        texto,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().split("\n")[0].strip()
    return None


# =============================================================================
# Extração de experiência
# =============================================================================

def extrair_experiencia(texto: str) -> float:
    texto_min = texto.lower().replace(",", ".")
    padroes = [
        r"(\d+(?:\.\d+)?)\s*anos?\s+de\s+experi[êe]ncia",
        r"experi[êe]ncia\s+de\s+(\d+(?:\.\d+)?)\s*anos?",
        r"(\d+(?:\.\d+)?)\s*anos?\s+na\s+[áa]rea",
        r"(\d+(?:\.\d+)?)\s*anos?\s+atuando",
        r"atuo\s+h[áa]\s+(\d+(?:\.\d+)?)\s*anos?",
    ]
    valores: list[float] = []
    for padrao in padroes:
        for match in re.findall(padrao, texto_min):
            try:
                valores.append(float(match))
            except ValueError:
                continue
    return max(valores) if valores else 0.0


# =============================================================================
# Extração de habilidades
# =============================================================================

def _extrair_habilidades_spacy(doc: Any, texto: str) -> list[str]:
    """
    Combina keyword matching direto com stem matching via tokens spaCy.

    Stem matching (token.lemma_[:6]) captura variações morfológicas:
      "equipes" → lemma "equipe" → stem "equip" → match "gestão de equipe"
      "máquinas" → lemma "máquina" → stem "maquin" → match "operador de máquinas"
    """
    encontradas: set[str] = set()
    texto_lower = texto.lower()

    # Método A: keyword direto
    for h in HABILIDADES_BASE:
        if h.lower() in texto_lower:
            encontradas.add(_normalizar(h))

    # Método B: stem dos tokens spaCy
    stems: set[str] = set()
    for token in doc:
        if (
            token.pos_ in ("NOUN", "PROPN", "ADJ", "VERB")
            and not token.is_stop
            and len(token.text) >= 4
        ):
            lemma = (token.lemma_ or token.text).lower()
            stems.add(lemma[:6])

    for h in HABILIDADES_BASE:
        termos_chave = [w.lower() for w in h.split() if len(w) >= 4]
        if not termos_chave:
            continue
        if all(any(s.startswith(t[:5]) for s in stems) for t in termos_chave):
            normalizada = _normalizar(h)
            if normalizada not in encontradas:
                encontradas.add(normalizada)

    return sorted(encontradas)


def _extrair_habilidades_regex(texto: str) -> list[str]:
    """Fallback por keyword puro, sem spaCy."""
    texto_lower = texto.lower()
    encontradas: set[str] = set()
    for h in HABILIDADES_BASE:
        if h.lower() in texto_lower:
            encontradas.add(_normalizar(h))
    return sorted(encontradas)


# =============================================================================
# Resumo local (sem LLM)
# =============================================================================

def gerar_resumo_local(
    nome: str,
    cargo: str | None,
    experiencia: float,
    habilidades: list[str],
) -> str:
    cargo_txt = cargo or "cargo não identificado"
    hab_txt = (
        ", ".join(habilidades[:6])
        if habilidades
        else "habilidades não identificadas automaticamente"
    )
    exp_txt = f"{experiencia:.1f} ano(s)" if experiencia >= 1 else "experiência inicial"
    return (
        f"{nome} possui perfil relacionado a {cargo_txt}, com {exp_txt} de experiência. "
        f"Habilidades identificadas: {hab_txt}."
    )


# =============================================================================
# Pipeline principal (síncrono)
# =============================================================================

def processar_curriculo(nome: str, texto: str) -> DadosCurriculo:
    """
    Executa extração de cargo, experiência, habilidades e resumo.

    Síncrono por design — chamado via asyncio.to_thread no router async.
    """
    nlp = _get_nlp()
    texto_nlp = texto[:8_000]  # limite seguro para o modelo pt

    if nlp is not None:
        doc = nlp(texto_nlp)
        cargo      = _extrair_cargo_spacy(doc, texto) or _extrair_cargo_regex(texto)
        habilidades = _extrair_habilidades_spacy(doc, texto)
    else:
        cargo       = _extrair_cargo_regex(texto)
        habilidades = _extrair_habilidades_regex(texto)

    experiencia = extrair_experiencia(texto)
    resumo = gerar_resumo_local(nome, cargo, experiencia, habilidades)

    return DadosCurriculo(
        texto=texto,
        cargo=cargo,
        experiencia_anos=experiencia,
        habilidades=habilidades,
        resumo=resumo,
    )


# =============================================================================
# Scoring de compatibilidade
# =============================================================================

def calcular_score(
    vaga_habilidades: str,
    vaga_requisitos: str,
    candidato_habilidades: str,
    experiencia_anos: float,
) -> tuple[float, list[str]]:
    alvo = set(_normalizar_lista(vaga_habilidades + "," + vaga_requisitos))
    cand = set(_normalizar_lista(candidato_habilidades))

    if not alvo:
        return 0.0, ["A vaga não possui habilidades suficientes para comparação."]

    intersecao    = alvo & cand
    score_hab     = len(intersecao) / len(alvo)
    bonus_exp     = min(experiencia_anos / 10, 0.25)
    score         = min(1.0, score_hab * 0.75 + bonus_exp)

    motivos: list[str] = []
    if intersecao:
        motivos.append("Compatibilidade em: " + ", ".join(sorted(intersecao)))
    else:
        motivos.append("Poucas habilidades em comum com a vaga.")
    if experiencia_anos > 0:
        motivos.append(f"Experiência informada: {experiencia_anos:.1f} ano(s).")

    return round(score * 100, 1), motivos


def _normalizar_lista(texto: str) -> list[str]:
    partes = re.split(r"[,;\n\|/]", texto.lower())
    return [p.strip() for p in partes if len(p.strip()) >= 3]