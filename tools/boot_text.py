"""Textos do BOOT.BIN do Let's Gakkou: offset no arquivo -> portugues. Cada um precisa caber no espaco original
(ate o proximo byte nao zero). Ficam como estao: as tabelas romaji -> kana do teclado (0xD0169-0xD0E05), a tabela
de kana do Shiritori (0xD5258-0xD539C) e a mensagem de depuracao de arquivo nao achado (0xD4394)."""
import struct

from gtext import to_bytes

# Shift-JIS desenhado com a fonte do sistema (acentos pelo JIS X 0213, como nos scripts)
SJIS = {
    0xD69D8: '"%s" não pode ser usado.',
    # descricoes do menu da escola
    0xD7280: "Começar a aula.",
    0xD7294: "Aulas de palavras e duelos de Shiritori.",
    0xD72C4: "Treinos e jogos-treino.",
    0xD72F0: "Comprar, provar e lavar fantasias.",
    0xD7320: "Aulas e mais, usando a internet.",
    0xD734C: "Veja o Caderno, o Placar e o Álbum.",
    0xD7380: "Salvar o jogo e ligar ao app de celular.",
    0xD73B4: "Ir para casa.",
    0xD73C4: "Férias!",
    0xD73D4: "Começa a cerimônia.",
    0xD73EC: "Começa a formatura.",
    # botoes
    0xD7514: "Ajuda",
    0xD751C: "Defesa",
    0xD7528: "Qtd.",
    0xD7534: "Confirmar",
    0xD7540: "Esquece",
    0xD75CC: "Começar",
    0xD75D8: "Esquece",
    0xD7610: "Fantasias",
    0xD91A4: "★%d",
    # caderno de palavras
    0xD948C: "Apagar já",
    0xD949C: "Esquece",
    0xD94A8: "Mudar leit.",
    0xD94B4: "Apagar pal.",
    0xDAAB0: "Cancelar",
    0xDAAE4: "Começar",
    0xDAAF0: "Apagar",
    0xDAAF8: "Esquece",
    # lavanderia de fantasias
    0xDAB6C: "%d un.",
    0xDAB7C: "Fantasia usada fica suja: lave antes de usar de novo.",
    0xDABC0: "Nenhuma fantasia precisa ser lavada.",
    0xDABF0: "Lavando…",
    0xDAC10: "Faltam ★ para lavar.",
    0xDAC4C: "Para lavar, é\npreciso ter ★.",
    0xDAC70: "1-3 un.",
    0xDAC78: "4-9 un.",
    0xDAC80: "10 ou +",
    # meses (3 bytes nos de 1 digito)
    0xDAD2C: "Jan", 0xDAD38: "Fev", 0xDAD48: "Mar", 0xDAD54: "Abr", 0xDAD60: "Mai", 0xDAD68: "Jun",
    0xDAD74: "Jul", 0xDAD80: "Ago", 0xDAD8C: "Set", 0xDAD9C: "Out", 0xDADAC: "Nov", 0xDADC0: "Dez",
    0xDAE94: "Salvar p/ fundo",
    0xDAEA4: "Esquece",
    0xDAEB8: "- Doko Demo Issyo - Partiu Escola!",
    0xDB1A8: "Sim",
    0xDB1B0: "Não",
}

# UTF-8 mostrado pelas janelas do sistema do PSP (save e dados do jogo)
UTF8 = {
    0xD83D4: "- Doko Demo Issyo - Partiu Escola!",
    0xD8408: "Registro do Prof.",
    0xD841C: '"Doko Demo Issyo" abriu uma escola! Toro, Jun, Ricky, Pierre e Suzuki: cinco alunos cheios de '
             "personalidade numa vida escolar animada. Let's School Life!",
    0xD8504: "O PSP entrou em modo de espera,\npor isso não foi possível salvar.",
    0xD8558: "O PSP entrou em modo de espera,\npor isso não foi possível carregar.",
    0xD85AC: "O PSP entrou em modo de espera,\npor isso não foi possível apagar.",
    0xD860C: "Não foi possível salvar.\nNão há Memory Stick™ inserido.",
    0xD8668: "Não foi possível carregar.\nNão há Memory Stick™ inserido.",
    0xD86C4: "Não foi possível apagar.\nNão há Memory Stick™ inserido.",
    0xD87A4: "Não foi possível carregar.\nNão há dados.",
    0xD87E8: "Não foi possível apagar.\nNão há dados.",
    0xD886C: "Não foi possível carregar.",
    0xD8890: "Não foi possível apagar.",
    0xD89C8: "Tentar apagar de novo?",
    0xD89F0: "Tentar carregar de novo?",
    0xD8A34: "O Memory Stick™ não tem espaço livre suficiente.\nPara salvar, faltam pelo menos\n%dKB livres.\n"
             "Apagar dados salvos que não são\nmais necessários para poder salvar?",
    0xD8B18: "Tentar salvar de novo?",
    0xD8B50: "Este jogo tem salvamento automático.\nDurante o salvamento, a luz de acesso do\n"
             '"Memory Stick Duo" pisca. Nesse momento,\nnão retire o Memory Stick™ nem\n'
             "desligue o aparelho.\nAtivar o salvamento automático?",
    0xD8CAC: "O Memory Stick™ foi retirado ou inserido.\nO salvamento automático será desligado.\nTudo bem?",
    0xD8D34: "Salvamento automático desligado.",
    0xD8D68: "Não há Memory Stick™.\nInsira um Memory Stick™ com\npelo menos %dKB livres.",
    0xD8DF4: "O salvamento automático será desligado.\nTudo bem?",
    0xD8E48: "Não foi possível salvar.\nNão há dados salvos de\n- Doko Demo Issyo - Partiu Escola!.",
    0xD8EC8: "Já existe um arquivo com o mesmo nome.",
}


# Codigo: endereco virtual -> (instrucao original, nova). O segmento comeca no byte 0x60 do arquivo.
# Teclado (rotina 0x8983C, chamada ao abrir): a1/a2/a3 dizem se as paginas kana/ABC/simbolos valem para o campo
# (tabela de tipos em 0xD49D8) e a pagina atual fica em +0x290, comecando sempre em 0 (kana). Passa a comecar no
# valor de a2: 1 (ABC) quando o campo aceita letras latinas (nomes e palavras), 0 nos campos so de kana.
CODE = {
    0x89868: (0xAC800290, 0xAC860290),  # sw zero, 0x290(a0) -> sw a2, 0x290(a0)
}
CODE_FILE_OFFSET = 0x60


def capacity(boot, off):
    end = boot.index(b"\0", off)
    while boot[end] == 0:
        end += 1
    return end - off - 1


def patch_boot(boot):
    """Devolve o BOOT.BIN traduzido; falha se algum texto nao couber."""
    out = bytearray(boot)
    for table, enc in ((SJIS, to_bytes), (UTF8, lambda t: t.encode("utf-8"))):
        for off, text in table.items():
            raw = enc(text)
            cap = capacity(boot, off)
            assert len(raw) <= cap, (hex(off), text, len(raw), cap)
            out[off:off + cap + 1] = raw + b"\0" * (cap + 1 - len(raw))
    for va, (old, new) in CODE.items():
        off = va + CODE_FILE_OFFSET
        assert struct.unpack_from("<I", boot, off)[0] == old, hex(va)
        struct.pack_into("<I", out, off, new)
    return bytes(out)
