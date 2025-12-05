# Simulação de deadlock e formas de resolver

Laboratório em Python que mostra:
- um deadlock clássico entre processos competindo por dois recursos;
- prevenção com ordenação global de locks;
- recuperação com retry, timeout e backoff;
- evitação com o algoritmo do banqueiro (estado seguro antes de conceder recursos);
- telemetria/estatísticas e exportação de métricas.

## Estrutura do projeto
- `main.py`: ponto de entrada.
- `cli.py`: parsing de argumentos e orquestração dos cenários.
- `config.py`: constantes globais (`HOLD_TIME`, `DEADLOCK_TIMEOUT`, `DEFAULT_RETRY_TIMEOUT`).
- `core/logging_utils.py`: logging e configuração do multiprocessing.
- `core/metrics.py`: coleta, resumo e exportação (JSON/CSV).
- `core/worker.py`: `Worker`, `NaiveWorker`, `RetryWorker`, `BankerWorker`.
- `core/scenario.py`: `Scenario` base e cenários (`DeadlockScenario`, `OrderedScenario`, `RetryScenario`, `BankerScenario`).
- `plot_metrics.py`: script opcional para gerar gráficos (matplotlib).

## Requisitos
- Python 3.8+ (somente biblioteca padrão).
- Para gráficos: `matplotlib` (`pip install matplotlib`).

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
python3 main.py banqueiro

# Progresso simples
python3 main.py deadlock --progress

# Exportar métricas
python3 main.py retry --metrics-out logs/dados.json --metrics-format json
python3 main.py todos --metrics-out logs/dados.csv --metrics-format csv

# Ajustar quantidade de processos (padrão: 2)
python3 main.py deadlock --workers 4 --progress
python3 main.py banqueiro --workers 4 --progress

# Ajustar quantidade de recursos (padrão: 2)
python3 main.py ordenado --resources 3 --workers 4 --progress

# No banqueiro, ajustar unidades por recurso (padrão: 1 para equivaler aos demais)
python3 main.py banqueiro --resources 2 --resource-units 1 --workers 4 --progress

# Plotar métricas (gera PNGs em logs/plots)
python3 plot_metrics.py logs/dados.json --output-dir logs/plots
```

## O que observar
- Deadlock: processos alternam ordens (ex.: crescente vs. decrescente); o pai detecta que não terminaram em `DEADLOCK_TIMEOUT` e encerra os processos.
- Ordem fixa: todos obedecem à mesma ordem global dos recursos, removendo o ciclo de espera.
- Retry/timeout: com ordens alternadas, cada processo desiste se não conseguir o próximo recurso no timeout, libera os já segurados, espera (backoff) e tenta de novo; eventualmente um progride.
- Banqueiro: cada processo declara a necessidade máxima; o "banqueiro" só concede pedidos que mantenham um estado seguro (há uma sequência possível de finalização). Os processos nunca entram em deadlock, apenas reagem com mais retries se não houver estado seguro.
- Resumo de métricas: duração por processo, retries (quando aplicável), tempo esperando recursos e médias por cenário. Se o ambiente bloquear `multiprocessing.Queue`, a telemetria é desativada automaticamente.

## Notas adicionais
- As constantes globais ficam em `config.py`. Ajuste `HOLD_TIME`, `DEADLOCK_TIMEOUT` ou `DEFAULT_RETRY_TIMEOUT` para experimentar.
- O script tenta usar `fork` (ou `spawn` como fallback) para contornar ambientes que forçam `forkserver`.
