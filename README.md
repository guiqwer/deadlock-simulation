# Simulação de deadlock e formas de resolver

Laboratório em Python que mostra:
- um deadlock clássico entre dois processos competindo por dois recursos;
- prevenção com ordenação global de locks;
- recuperação com retry, timeout e backoff;
- telemetria/estatísticas e exportação de métricas.

## Estrutura do projeto
- `main.py`: ponto de entrada.
- `cli.py`: parsing de argumentos e orquestração dos cenários.
- `config.py`: constantes globais (`HOLD_TIME`, `DEADLOCK_TIMEOUT`, `DEFAULT_RETRY_TIMEOUT`).
- `core/logging_utils.py`: logging e configuração do multiprocessing.
- `core/metrics.py`: coleta, resumo e exportação (JSON/CSV).
- `core/worker.py`: `Worker`, `NaiveWorker`, `RetryWorker`.
- `core/scenario.py`: `Scenario` base e cenários (`DeadlockScenario`, `OrderedScenario`, `RetryScenario`).

## Requisitos
- Python 3.8+ (somente biblioteca padrão).

## Como executar
No diretório do projeto:
```bash
# Ajuda
python3 main.py --help

# Rodar os três cenários em sequência
python3 main.py todos

# Rodar um cenário específico
python3 main.py deadlock
python3 main.py ordenado
python3 main.py retry

# Progresso simples
python3 main.py deadlock --progress

# Exportar métricas
python3 main.py retry --metrics-out logs/dados.json --metrics-format json
python3 main.py todos --metrics-out logs/dados.csv --metrics-format csv
```

## O que observar
- Deadlock: P1 e P2 pegam recursos em ordem inversa; o pai detecta que não terminaram em `DEADLOCK_TIMEOUT` e encerra os processos.
- Ordem fixa: ambos obedecem A → B, removendo o ciclo de espera.
- Retry/timeout: com ordem inversa, cada processo desiste se o segundo lock não vier rápido, libera o primeiro, espera (backoff) e tenta de novo; eventualmente um progride.
- Resumo de métricas: duração por processo, retries (quando aplicável) e médias por cenário. Se o ambiente bloquear `multiprocessing.Queue`, a telemetria é desativada automaticamente.

## Notas adicionais
- As constantes globais ficam em `config.py`. Ajuste `HOLD_TIME`, `DEADLOCK_TIMEOUT` ou `DEFAULT_RETRY_TIMEOUT` para experimentar.
- O script tenta usar `fork` (ou `spawn` como fallback) para contornar ambientes que forçam `forkserver`.
