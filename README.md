<p align="center">
  <img src="art/logo.png" alt="Doko Demo Issyo: Partiu Escola!" width="640">
</p>

<p align="center">Tradução para o português do Brasil de <i>Doko Demo Issho: Let's Gakkou!</i> (PSP).</p>

## Baixar

A versão atual é a **v0.2**, uma versão de teste. O patch fica na página de [Releases](https://github.com/BryanSeliga/Doko-Demo-Issyo-Partiu-Escola-/releases), e as notas de cada versão dizem o que mudou e o que ainda não foi testado.

## Como aplicar

1. Tenha a ISO japonesa original do jogo (UCJS10039). O patch não contém o jogo.
2. Aplique o arquivo `.xdelta` na ISO com o Delta Patcher ou o xdelta3.
3. Confira o SHA-1 da ISO original e da ISO traduzida com os das notas da versão.

O patch tem checksum: se a ISO não for a esperada ou o download vier corrompido, o aplicador dá erro em vez de gerar uma ISO quebrada.

## O que está em português

- Todas as falas e aulas, a tela-título, os menus, as mensagens do sistema e as placas dos cenários.
- O vocabulário inicial e os nomes padrão dos Pokepi.
- O Shiritori, que encadeia as palavras pelas letras: a última letra de uma palavra é a primeira da seguinte, sem contar o acento.
- O Caderno, que agrupa as palavras pela inicial.

Ficam em japonês de propósito os nomes da equipe nos créditos, duas aulas que ensinam a ler kanji e alguns textos pequenos demais nos cenários.

Até agora o patch só foi testado no emulador PPSSPP.

## Neste repositório

- `traducao/`: os textos traduzidos, só com o número de cada fala e o texto em português.
- `tools/`: os programas que extraem os textos, montam a ISO traduzida e geram o patch.
- `docs/GUIA_TRADUCAO.md`: o guia de estilo da tradução.

Nenhum arquivo do jogo original está aqui.
