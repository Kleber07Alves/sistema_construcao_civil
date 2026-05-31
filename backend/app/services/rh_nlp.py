import os
import re
from dataclasses import dataclass

import fitz

HABILIDADES_BASE = [
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
]

CARGOS_BASE = [
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
]


@dataclass
class DadosCurriculo:
    texto: str
    cargo: str | None
    experiencia_anos: float
    habilidades: list[str]
    resumo: str


def extrair_texto_pdf(conteudo: bytes) -> str:
    with fitz.open(stream=conteudo, filetype="pdf") as doc:
        textos = [page.get_text() for page in doc]
    return "\n".join(textos).strip()


def _carregar_spacy():
    try:
        import spacy

        try:
            return spacy.load("pt_core_news_sm")
        except OSError:
            return spacy.blank("pt")
    except Exception:
        return None


def extrair_cargo(texto: str) -> str | None:
    texto_min = texto.lower()
    for cargo in CARGOS_BASE:
        if cargo in texto_min:
            return cargo

    padrao = re.search(r"cargo\s*[:\-]\s*([A-Za-zÀ-ÿ\s]{3,80})", texto, re.IGNORECASE)
    if padrao:
        return padrao.group(1).strip().split("\n")[0]
    return None


def extrair_experiencia(texto: str) -> float:
    texto_min = texto.lower().replace(",", ".")
    padroes = [
        r"(\d+(?:\.\d+)?)\s*anos?\s+de\s+experi[êe]ncia",
        r"experi[êe]ncia\s+de\s+(\d+(?:\.\d+)?)\s*anos?",
        r"(\d+(?:\.\d+)?)\s*anos?\s+na\s+[áa]rea",
    ]
    valores = []
    for padrao in padroes:
        for match in re.findall(padrao, texto_min):
            try:
                valores.append(float(match))
            except ValueError:
                continue
    return max(valores) if valores else 0.0


def extrair_habilidades(texto: str) -> list[str]:
    texto_min = texto.lower()
    encontradas = []
    for habilidade in HABILIDADES_BASE:
        if habilidade in texto_min:
            normalizada = habilidade.replace("eletrica", "elétrica").replace("hidraulica", "hidráulica")
            normalizada = normalizada.replace("seguranca", "segurança").replace("gestao", "gestão")
            if normalizada not in encontradas:
                encontradas.append(normalizada)
    return encontradas


def gerar_resumo_local(nome: str, cargo: str | None, experiencia: float, habilidades: list[str]) -> str:
    cargo_txt = cargo or "cargo não identificado"
    habilidades_txt = ", ".join(habilidades[:6]) if habilidades else "habilidades não identificadas automaticamente"
    return (
        f"{nome} possui perfil relacionado a {cargo_txt}, com aproximadamente {experiencia:.1f} ano(s) de experiência. "
        f"Habilidades identificadas: {habilidades_txt}."
    )


def processar_curriculo(nome: str, texto: str) -> DadosCurriculo:
    nlp = _carregar_spacy()
    if nlp:
        # O spaCy é carregado para manter a arquitetura de NLP proposta. A extração principal usa regras simples,
        # porque isso deixa o MVP mais previsível para estudo e apresentação.
        _ = nlp(texto[:1000])

    cargo = extrair_cargo(texto)
    experiencia = extrair_experiencia(texto)
    habilidades = extrair_habilidades(texto)
    resumo = gerar_resumo_local(nome, cargo, experiencia, habilidades)
    return DadosCurriculo(
        texto=texto,
        cargo=cargo,
        experiencia_anos=experiencia,
        habilidades=habilidades,
        resumo=resumo,
    )


def calcular_score(vaga_habilidades: str, vaga_requisitos: str, candidato_habilidades: str, experiencia_anos: float) -> tuple[float, list[str]]:
    alvo = set(_normalizar_lista(vaga_habilidades + "," + vaga_requisitos))
    cand = set(_normalizar_lista(candidato_habilidades))

    if not alvo:
        return 0.0, ["A vaga não possui habilidades suficientes para comparação."]

    intersecao = alvo.intersection(cand)
    score_habilidades = len(intersecao) / len(alvo)
    bonus_experiencia = min(experiencia_anos / 10, 0.25)
    score = min(1.0, score_habilidades * 0.75 + bonus_experiencia)

    motivos = []
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
