# Lapid.ai — sistema visual ("turno da noite")

**Ideia central.** O produto é um desenvolvedor que trabalha enquanto você dorme. A interface gira em torno
de um objeto próprio: o **relógio de 24h**, que mostra a que hora do dia os relatos chegam. Ele aparece na
visão geral (dados reais) e no login (decorativo). Nada de cartões de métricas iguais.

## Decisões e por quê
- **Trilho superior no lugar de sidebar**: libera largura para tabelas e feeds e foge do layout SaaS padrão.
- **Seções com fio, não caixas**: listas e tabelas "ruled" (linhas finas) em vez de cartões empilhados.
  Painéis arredondados (22px) só onde há formulário.
- **Ciano é sinal, não decoração**: aparece apenas em "vivo/novo/pico" e no item ativo da navegação.
  A estrutura é azul ultramarino.
- **Situação nunca só por cor**: todo chip tem ponto + texto.
- **Movimento**: uma única coreografia (barras do relógio crescendo, escalonadas) e um pulso lento no logotipo.
  Respeita `prefers-reduced-motion`.

## Tokens
| Token | Valor | Uso |
|---|---|---|
| `--abyss` | `#050816` | fundo |
| `--deck` / `--deck-2` | `#0b1127` / `#111a38` | superfícies |
| `--hair` / `--hair-2` | `#1b2650` / `#2a396f` | fios e bordas |
| `--paper` | `#eef3ff` | texto |
| `--haze` | `#8fa0c8` | texto secundário (≥ 6:1 sobre o fundo) |
| `--ultra` | `#3560f0` | ações primárias (branco sobre ele ≥ 4,5:1) |
| `--signal` | `#4fe3f5` | vivo, novo, foco |
| `--amber` / `--mint` / `--rose` | `#f5b74a` / `#4ade9c` / `#ff7a8a` | análise / resolvido / erro |

## Tipografia
- **Bricolage Grotesque** (títulos e números, eixo de largura condensado): personalidade sem excesso.
- **Hanken Grotesk** (texto): leitura limpa em tamanho 15px, entrelinha 1,6.
- **JetBrains Mono**: apenas protocolos, código e stack traces.

> As fontes vêm do Google Fonts (liberado no CSP). Para hospedar localmente (recomendado por LGPD),
> baixe os `.woff2`, coloque em `frontend/static/fonts/`, declare `@font-face` no CSS e remova
> `fonts.googleapis.com`/`fonts.gstatic.com` do CSP em `backend/routes/admin.py`.

## Acessibilidade (checklist da skill UI/UX Pro Max)
Contraste ≥ 4,5:1 · foco visível (anel ciano) · alvos de toque ≥ 44px · `aria-current` na navegação ·
SVGs com `role="img"` e rótulo · sem estilos inline (CSP estrito) · responsivo 375/768/1024/1440.
