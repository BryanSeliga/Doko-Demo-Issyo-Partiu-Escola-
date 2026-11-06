# Guia de tradução PT-BR — Let's Gakkou (Partiu Escola!)

Traduza do japonês para **português brasileiro natural**, como se o jogo tivesse sido feito aqui. Não traduza palavra por palavra.

## O jogo

*Doko Demo Issyo: Let's Gakkou!* é a continuação de *Doko Demo Issyo*. Os Pokepi agora vão à escola: quem joga é **professor ou professora** e ensina palavras e matérias aos Pokepi, que usam essas palavras nas conversas, nas aulas, nos clubes e nos passeios. O diretor da escola é o Kuro.

Texto leve, fofo e engraçado, para todas as idades. Humor e carinho importam mais que a literalidade: adapte piadas e trocadilhos para funcionarem em português.

## Personagens e voz

| Japonês | PT-BR | Voz e tique |
|---|---|---|
| トロ | Toro | Gatinho branco. Doce, curioso e ingênuo, um pouco criança. Fala informal e carinhosa. Tique ニャ/ニャ～: ", miau" no fim da frase. |
| ピエール | Pierre | Cachorro vaidoso e dramático, de fala afetada e cheia de charme. Adora culinária, moda e tudo que é francês. Fala de si no masculino. Expressões: "Ai, que chique!", "Credo!", "meu bem". Tique わン/ワン: ", au" no fim da frase. |
| リッキー | Ricky | Sapo caipira, simples e animado, que vive treinando para ser o mais forte do mundo. Caipira leve ("uai", "sô", "num é?"), sem exagerar na grafia. Fala de si no masculino; オラ = "eu". Tiques: ケロ = ", croac"; ダス/ッス = ", sô". |
| スズキ | Suzuki | Robô que se acha ultra-avançado: orgulhoso, professoral e ingênuo. "Pois é!", "Eis a questão!", "Calculando~". Fala de si no masculino. Tique ロボ no fim: ", robô". ロボット no meio da frase é só "robô". |
| ジュン | Jun | Coelha alegre, moderninha e espevitada, com jeito de adolescente: gíria leve ("Valeu!", "Aff", "Tipo assim"). Fala de si no feminino. Tiques: ピョン = ", pyon"; ウサ = ", usa" (falas tristes ou sem graça). |
| クロ | Kuro, o diretor | Gato preto, diretor da escola: brincalhão, meio mandão e convencido, mas gente boa. Tique みャ: ", miau" no fim da frase (o mesmo do Toro, com cara de chefe). |
| サル / ピポサル | Macaco / Macacos Pipo | Macacos que querem conquistar a escola e o mundo. Tique ッキ/ウッキー: ", uki" no fim da frase; "Ukiii!" como grito. |
| 先生 | Prof. (quem joga) | Sempre neutro em gênero (ver regra 3). Com nome antes, "Prof. {nome}". |
| ポケピ | Pokepi | |
| コトバ / ことば | palavra | |
| 校長 | diretor | |

Fale com quem joga usando **você**, sem gíria datada ou palavrão. Prefira frases curtas, com cara de fala. Mantenha os alongamentos e a alegria do original: "Sim~!", "Eba!", "Hmm...".

## Regras obrigatórias

**1. Variáveis são intocáveis.** Mantenha exatamente a mesma quantidade de cada marcador; pode mudar a ordem para a frase soar natural.

- `{16}{14:0001}{16}`: palavra inserida pelo jogo, muitas vezes ensinada por quem joga. Mantenha o trio inteiro.
- `{16}{1d}{16}`: nome inserido pelo jogo (um Pokepi, uma pessoa ou uma palavra). Mantenha o trio inteiro.
- `{14:0000}`, `{14:000b}`, `{1b:12e8}` e semelhantes: número, palavra ou nome inserido pelo jogo.
- `$Neko`, `$Robo`, `$Kaeru` e outros começados por `$`: marcadores do jogo no começo do texto. Mantenha no mesmo lugar e traduza o resto.

**2. As variáveis podem ser qualquer palavra.** Não se sabe o gênero nem o número. Não coloque artigo antes delas nem concorde com elas. Reescreva a frase para ficar neutra: "Gosto de {16}{14:0001}{16}", "Isso de {16}{14:0001}{16} é legal".

**3. Quem joga pode ser homem ou mulher.** Evite formas com gênero para essa pessoa. Use "Prof." em vez de "professor/professora", e em vez de "Você está cansado?" use "Você parece sem energia?".

**4. Mantenha a estrutura de cada texto.**

- O balão de fala quebra as linhas sozinho, por palavra, e passa de página sozinho. Em falas, **não** precisa manter as quebras de linha (`\n`) do japonês; mantenha só quando a quebra separa coisas de propósito (lista, pausa dramática).
- Textos curtos do tipo `pool` costumam ser opções de resposta, nomes de itens, categorias ou títulos de aula, e aparecem em caixas que **não** quebram linha: traduza de forma enxuta, com até uns 14 caracteres por linha.
- Espaço no início ou no fim do japonês indica um pedaço de frase que será colado a outro. Mantenha esse espaço.
- Textos seguidos no lote costumam ser a mesma conversa, e um pensamento pode continuar no próximo. Leia os vizinhos antes de traduzir.
- Nenhum texto pode passar de 600 bytes (o jogo trava acima de uns 1000). O maior original tem 265.

**5. Caracteres.** A fonte do PSP tem ASCII, `á à â ã é ê í ó ô õ ú ü ç` (e maiúsculas), `♪`, `…` e `～`.

- Escreva `~` onde o japonês tem `～` (a montagem troca pelo `～` do jogo).
- Use `!` e `?` em vez de `！` e `？`. Use aspas retas `"` em vez de `「」`.
- Não deixe japonês na tradução. Nomes japoneses ficam em letras latinas.
- Não use emoji, travessão longo, `♥` ou barra invertida.

**6. Palavras e assuntos japoneses.** Traduza ou adapte comidas, costumes e matérias quando houver equivalente natural. Mantenha nomes japoneses conhecidos em letras latinas (sushi, Tóquio, Kyoto). Quando o assunto é a própria língua japonesa (leitura de kanji, "como se lê", trocadilhos com sílabas), adapte para falar de "como se escreve", "como se fala" ou do sentido da palavra.

**7. Detalhes recorrentes.**

- `♪` aparece no jogo: mantenha onde o japonês tiver.
- Número variável pode ser 1 ou mais: use uma forma que sirva aos dois, como "palavra(s) nova(s)".
- Honoríficos: com nome, mantenha em letras latinas (-san, -chan, -kun) ou tire se soar estranho; 先生 sozinho = "Prof.".

## Exemplos

| Japonês | Português |
|---|---|
| 校長の クロです みャ | Eu sou o Kuro, o diretor, miau. |
| 今日から、先生として 働いてもらう みャ | A partir de hoje, você vai trabalhar aqui como Prof., miau. |
| `{16}{14:0001}{16}って 好きニャ？` | `Você gosta de {16}{14:0001}{16}, miau?` |
| `{16}{14:0001}{16}って なんて 読むッキ？` | `Como se fala {16}{14:0001}{16}, uki?` |
| 別のを おしえてケロ (pool) | Me ensina outra, croac. |
| その他 (pool) | Outros |
