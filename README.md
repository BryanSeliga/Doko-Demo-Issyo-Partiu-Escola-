<p align="center">
  <img src="art/logo.png" alt="Doko Demo Issyo: Partiu Escola!" width="640">
</p>

<p align="center">Tradução para o português do Brasil de <i>Doko Demo Issho: Let's Gakkou!</i> (PSP).</p>

## Baixar

A versão atual é a **v1.0**. O patch fica na página de [Releases](https://github.com/BryanSeliga/Doko-Demo-Issyo-Partiu-Escola-/releases), e as notas de cada versão dizem o que mudou e o que ainda não foi testado.

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
- O teclado, que tem as letras acentuadas e o cê-cedilha na página de símbolos. As palavras ensinadas podem ter até 12 letras.
- Os selos de avaliação das aulas e dos clubes.
- O que o menu do PSP mostra para o jogo: o título, o ícone, o vídeo do ícone e o painel de informações.

Ficam em japonês de propósito os nomes da equipe nos créditos, duas aulas que ensinam a ler kanji e alguns textos pequenos demais nos cenários.

Até agora o patch só foi testado no emulador PPSSPP. O menu do PSP e o vídeo do ícone não aparecem no emulador e nunca foram vistos num console de verdade.

## Neste repositório

- `traducao/`: os textos traduzidos, só com o número de cada fala e o texto em português.
- `tools/`: os programas que extraem os textos, montam a ISO traduzida e geram o patch. Para refazer o vídeo do ícone, o montador usa o ffmpeg do pacote `imageio-ffmpeg`; sem ele, o vídeo original fica.
- `art/`: o logotipo em português.
- `docs/GUIA_TRADUCAO.md`: o guia de estilo da tradução.

Nenhum arquivo do jogo original está aqui.
