"""
Extrator v2 de .bra (formato PDA) - Way of the Samurai 3

Estrutura do arquivo:
  cabecalho (16 bytes): b"PDA\\0", versao, OFFSET_DO_INDICE, quantidade
  blocos: [tam_descomp u32][tam_comp u32][0 u32][6 u32] + deflate "cru"
  indice (no OFFSET_DO_INDICE): 8 bytes zerados, depois 1 entrada por bloco:
      [tam_comp u32][tam_descomp u32][tam_nome u16][0x21 u16][offset u32]
      [nome (tam_nome bytes)][8 bytes zerados]   (a ultima entrada nao tem os 8 zeros)

Extensoes: .l = tabelas/dialogos, .sx = scripts de cenario, .nif = modelo/textura, .ogg = audio
"""
import csv
import os
import struct
import sys
import zlib

CAMINHO = r"C:\Program Files (x86)\Steam\steamapps\common\Way of the Samurai 3\US.bra"
SAIDA = r"C:\Users\pache\OneDrive\Área de Trabalho\extrair video\US_nomeado"
PULAR_AUDIO = True   # True = nao extrai os .ogg (325 MB de vozes)

if len(sys.argv) > 1:
    CAMINHO = sys.argv[1]
    SAIDA = os.path.splitext(CAMINHO)[0] + "_nomeado"


def ler_indice(f, tamanho_arquivo):
    magic, versao, off_indice, qtd = struct.unpack("<4sIII", f.read(16))
    if magic != b"PDA\x00":
        raise SystemExit("ERRO: nao e um .bra do tipo PDA.")
    f.seek(off_indice)
    cauda = f.read()
    entradas = []
    p = 8
    for _ in range(qtd):
        cs, us, nl, flag, off = struct.unpack_from("<IIHHI", cauda, p)
        nome = cauda[p + 16: p + 16 + nl].decode("cp932", "replace")
        entradas.append((nome, off, cs, us))
        p += 24 + nl
    return versao, off_indice, qtd, entradas


def caminho_seguro(nome):
    partes = [x for x in nome.replace("/", "\\").split("\\") if x and x not in (".", "..")]
    return os.path.join(SAIDA, *partes)


def main():
    tam = os.path.getsize(CAMINHO)
    print("Arquivo:", CAMINHO, "-", tam, "bytes")
    os.makedirs(SAIDA, exist_ok=True)
    ok = erros = pulados = 0

    with open(CAMINHO, "rb") as f:
        versao, off_indice, qtd, entradas = ler_indice(f, tam)
        print("Versao:", versao, "| indice em:", off_indice, "| entradas:", len(entradas), "(cabecalho diz", qtd, ")")

        with open(os.path.join(SAIDA, "_indice.csv"), "w", newline="", encoding="utf-8-sig") as fcsv:
            w = csv.writer(fcsv)
            w.writerow(["bloco", "nome", "offset", "tam_comp", "tam_descomp"])
            for i, (nome, off, cs, us) in enumerate(entradas):
                w.writerow([i, nome, off, cs, us])
                if PULAR_AUDIO and nome.lower().endswith(".ogg"):
                    pulados += 1
                    continue
                if off + 16 + cs > tam:
                    print("AVISO: bloco", i, nome, "fora do arquivo (arquivo cortado?)")
                    erros += 1
                    continue
                f.seek(off)
                us2, cs2, zero, nivel = struct.unpack("<4I", f.read(16))
                if (cs2, us2) != (cs, us):
                    print("AVISO: bloco", i, nome, "- indice e cabecalho do bloco divergem")
                try:
                    dados = zlib.decompress(f.read(cs), -15)
                except zlib.error as e:
                    print("ERRO ao descomprimir", nome, e)
                    erros += 1
                    continue
                destino = caminho_seguro(nome)
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with open(destino, "wb") as out:
                    out.write(dados)
                ok += 1
                if ok % 200 == 0:
                    print("...", ok, "arquivos")

    print("Extraidos:", ok, "| pulados (audio):", pulados, "| erros:", erros)
    print("Saida em:", SAIDA)


main()