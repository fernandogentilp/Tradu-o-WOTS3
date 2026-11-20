"""
Extrator de .bra (formato "PDA") - Way of the Samurai 3

Formato (descoberto pela amostra de 2 MB):
  cabecalho (16 bytes): b"PDA\\0", versao, valor_total, quantidade
  depois, blocos em sequencia, cada um:
      [tam_descomprimido u32][tam_comprimido u32][0 u32][6 u32]
      + dados comprimidos em deflate "cru" (zlib sem cabecalho)

Uso: python extrair_bra.py            (usa os caminhos abaixo)
     python extrair_bra.py arq.bra    (outro arquivo, saida na mesma pasta)
"""
import csv
import os
import re
import struct
import sys
import zlib

CAMINHO = r"C:\Program Files (x86)\Steam\steamapps\common\Way of the Samurai 3\US.bra"
SAIDA = r"C:\Users\pache\OneDrive\Área de Trabalho\extrair video\US_extraido"

if len(sys.argv) > 1:
    CAMINHO = sys.argv[1]
    SAIDA = os.path.splitext(CAMINHO)[0] + "_extraido"

# trechos de texto UTF-16 (>= 8 letras ASCII seguidas) -> ajuda a achar tabelas de texto
RE_UTF16 = re.compile(rb"(?:[ -~]\x00){8,}")


def tipo_do_bloco(dados):
    if dados.startswith(b"Gamebryo File Format"):
        return "nif"
    if dados.startswith(b"DDS "):
        return "dds"
    if dados.startswith(b"OggS"):
        return "ogg"
    if dados.startswith(b"RIFF"):
        return "wav"
    # lista de texto UTF-16 puro (ex.: lista de cenarios)
    topo = dados[:60]
    if len(topo) >= 20 and all(topo[i] == 0 for i in range(1, 20, 2)):
        return "utf16.txt"
    return "bin"


def main():
    os.makedirs(SAIDA, exist_ok=True)
    tamanho_arquivo = os.path.getsize(CAMINHO)
    print("Arquivo:", CAMINHO)
    print("Tamanho:", tamanho_arquivo, "bytes")

    with open(CAMINHO, "rb") as f, open(
        os.path.join(SAIDA, "_indice.csv"), "w", newline="", encoding="utf-8-sig"
    ) as fcsv:
        cab = f.read(16)
        magic, versao, valor_total, quantidade = struct.unpack("<4sIII", cab)
        print("Cabecalho:", magic, versao, valor_total, quantidade)
        if magic != b"PDA\x00":
            print("ERRO: nao parece um .bra do tipo PDA. Me manda esta saida.")
            return

        w = csv.writer(fcsv)
        w.writerow(["bloco", "offset", "tam_descomp", "tam_comp", "tipo", "trechos_texto", "previa"])

        i = 0
        soma_descomp = 0
        while True:
            pos = f.tell()
            h = f.read(16)
            if len(h) == 0:
                print("Fim do arquivo alcancado.")
                break
            if len(h) < 16:
                print("AVISO: sobraram", len(h), "bytes no fim (cabecalho incompleto).")
                break
            us, cs, zero, nivel = struct.unpack("<4I", h)
            if zero != 0 or nivel != 6:
                print("PAROU no bloco", i, "offset", hex(pos), "- cabecalho diferente do esperado:", us, cs, zero, nivel)
                print("(Me manda esta mensagem; pode ser outro tipo de dado depois dos blocos.)")
                break
            comp = f.read(cs)
            if len(comp) < cs:
                print("AVISO: bloco", i, "cortado (arquivo incompleto?).")
                break
            try:
                dados = zlib.decompress(comp, -15)
            except zlib.error as e:
                print("ERRO ao descomprimir bloco", i, "offset", hex(pos), e)
                break
            if len(dados) != us:
                print("AVISO: bloco", i, "tem", len(dados), "bytes, esperado", us)

            ext = tipo_do_bloco(dados)
            nome = "%05d.%s" % (i, ext)
            with open(os.path.join(SAIDA, nome), "wb") as out:
                out.write(dados)

            trechos = RE_UTF16.findall(dados)
            previa = trechos[0].decode("utf-16le", "replace")[:60] if trechos else ""
            w.writerow([i, hex(pos), us, cs, ext, len(trechos), previa])

            soma_descomp += len(dados)
            i += 1
            if i % 250 == 0:
                print("...", i, "blocos")

    print("Blocos extraidos:", i, "(cabecalho diz:", quantidade, ")")
    print("Soma descomprimida:", soma_descomp, "(cabecalho diz:", valor_total, ")")
    print("Saida em:", SAIDA)
    print("Veja o arquivo _indice.csv nessa pasta.")


main()