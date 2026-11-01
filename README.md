# AOC Monitor Control (24B1W)

Aplicativo utilitário em Python / GTK 3 para Linux Mint (XFCE / X11) para gerenciar o sinal VGA do monitor AOC 24B1W, corrigir barras pretas laterais, ajustar resolução e deslocamento manual (offset/scale).

## Estrutura do Projeto

* `src/main.py`: Código-fonte principal da aplicação GTK.
* `desktop/aoc-monitor-fix.desktop`: Arquivo de atalho para o menu do sistema.
* `install.sh`: Script para instalar/atualizar a versão do sistema.

## Instalação no Sistema

Para instalar ou atualizar o executável no seu sistema:

```bash
chmod +x install.sh
./install.sh
```

## Execução direta

```bash
python3 src/main.py
```
