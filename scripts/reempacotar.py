"""
Reempacotador de .bra (formato PDA) - Way of the Samurai 3

Pega os arquivos modificados de uma pasta (com a MESMA estrutura de nomes do .bra,
ex.: MODS\\US\\GameText\\GameText.l) e gera um .bra novo. O original NAO e alterado.

Como funciona: blocos nao modificados sao copiados como estao; os modificados sao
recomprimidos (deflate nivel 6); depois o indice do fim do arquivo e o cabecalho
(posicao do indice) sao reescritos com as posicoes novas.

COMO USAR
  1) coloque os arquivos modificados em MODS, com o caminho igual ao do .bra
     (ex.: <MODS>\\US\\GameText\\GameText.l)
  2) rode o script -> cria US_novo.bra na pasta SAIDA
  3) FACA BACKUP do US.bra original, depois copie o US_novo.bra pra pasta do jogo
     com o nome US.bra
"""
import os
import struct
import sys
import zlib

BASE = r"C:\Users\pache\OneDrive\Área de Trabalho\extrair video"
ORIGINAL = r"C:\Program Files (x86)\Steam\steamapps\common\Way of the Samurai 3\US.bra"
MODS = BASE + r"\MODS"
NOVO = BASE + r"\US_novo.bra"

if len(sys.argv) >= 4:
    ORIGINAL, MODS, NOVO = sys.argv[1:4]


def ler_indice(f):
    magic, versao, off_indice, qtd = struct.unpack("<4sIII", f.read(16))
    if magic != b"PDA\x00":
        raise SystemExit("ERRO: nao e um .bra do tipo PDA.")
    f.seek(off_indice)
    cauda = f.read()
    entradas = []
    p = 8
    for _ in range(qtd):
        cs, us, nl, flag, off = struct.unpack_from("<IIHHI", cauda, p)
        nome = cauda[p + 16: p + 16 + nl]
        entradas.append({"nome": nome, "flag": flag, "off": off, "cs": cs, "us": us})
        p += 24 + nl
    return versao, off_indice, qtd, entradas


def achar_mods(pasta, entradas):
    por_nome = {e["nome"].decode("cp932").lower(): i for i, e in enumerate(entradas)}
    mods = {}
    desconhecidos = []
    for raiz, _, arqs in os.walk(pasta):
        for a in arqs:
            caminho = os.path.join(raiz, a)
            rel = os.path.relpath(caminho, pasta).replace("/", "\\").lower()
            if rel in por_nome:
                mods[por_nome[rel]] = caminho
            else:
                desconhecidos.append(rel)
    return mods, desconhecidos


def main():
    if os.path.abspath(NOVO) == os.path.abspath(ORIGINAL):
        raise SystemExit("ERRO: a saida nao pode ser o proprio arquivo original.")
    with open(ORIGINAL, "rb") as f:
        versao, off_indice, qtd, entradas = ler_indice(f)
    print("Original:", ORIGINAL, "| blocos:", qtd)

    mods, desc = achar_mods(MODS, entradas)
    if desc:
        print("AVISO: arquivos na pasta MODS que nao existem no .bra (ignorados):")
        for d in desc:
            print("   ", d)
    if not mods:
        raise SystemExit("Nenhum arquivo modificado encontrado em " + MODS)
    print("Arquivos a substituir:", len(mods))

    novas = []   # (cs, us, off) por entrada
    with open(ORIGINAL, "rb") as fo, open(NOVO, "wb") as fn:
        fn.write(struct.pack("<4sIII", b"PDA\x00", versao, 0, qtd))   # offset do indice entra no fim
        for i, e in enumerate(entradas):
            off_novo = fn.tell()
            if i in mods:
                dados = open(mods[i], "rb").read()
                c = zlib.compressobj(6, zlib.DEFLATED, -15)
                comp = c.compress(dados) + c.flush()
                fn.write(struct.pack("<4I", len(dados), len(comp), 0, 6))
                fn.write(comp)
                novas.append((len(comp), len(dados), off_novo))
                print("  substituido: %-45s %8d -> %8d bytes (comprimido %d)" %
                      (e["nome"].decode("cp932"), e["us"], len(dados), len(comp)))
            else:
                fo.seek(e["off"])
                fn.write(fo.read(16 + e["cs"]))
                novas.append((e["cs"], e["us"], off_novo))

        off_indice_novo = fn.tell()
        fn.write(b"\0" * 8)
        for i, e in enumerate(entradas):
            cs, us, off = novas[i]
            fn.write(struct.pack("<IIHHI", cs, us, len(e["nome"]), e["flag"], off))
            fn.write(e["nome"])
            if i != len(entradas) - 1:
                fn.write(b"\0" * 8)
        fn.seek(8)
        fn.write(struct.pack("<I", off_indice_novo))

    # confere o resultado lendo de volta
    with open(NOVO, "rb") as f:
        v2, oi2, q2, ent2 = ler_indice(f)
        assert q2 == qtd and v2 == versao
        for i, e in enumerate(ent2):
            f.seek(e["off"])
            us, cs, z, lv = struct.unpack("<4I", f.read(16))
            assert (us, cs) == (e["us"], e["cs"]) and z == 0 and lv == 6, "bloco %d inconsistente" % i
        for i, caminho in mods.items():
            f.seek(ent2[i]["off"] + 16)
            dados = zlib.decompress(f.read(ent2[i]["cs"]), -15)
            assert dados == open(caminho, "rb").read(), "bloco %d nao confere" % i
    print("Conferido. Arquivo criado:", NOVO, "(%d bytes)" % os.path.getsize(NOVO))
    print("Backup do US.bra original ANTES de copiar este pra pasta do jogo (renomeie pra US.bra).")


main()