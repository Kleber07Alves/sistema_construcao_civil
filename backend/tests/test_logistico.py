from app.models import NivelAlerta, Prioridade
from app.services.logistico_ml import classificar_alerta


def test_alerta_vermelho_por_probabilidade_alta():
    assert classificar_alerta(0.86, Prioridade.baixa) == NivelAlerta.vermelho


def test_alerta_vermelho_por_prioridade_alta():
    assert classificar_alerta(0.65, Prioridade.alta) == NivelAlerta.vermelho


def test_alerta_amarelo_para_prioridade_media():
    assert classificar_alerta(0.50, Prioridade.media) == NivelAlerta.amarelo


def test_alerta_verde_para_baixa_probabilidade():
    assert classificar_alerta(0.30, Prioridade.alta) == NivelAlerta.verde
