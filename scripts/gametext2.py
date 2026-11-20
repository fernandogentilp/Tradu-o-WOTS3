"""
GameText.l  <->  CSV   (Way of the Samurai 3)

Formato do GameText.l (decifrado):
  u32 quantidade_de_ponteiros (5074), u32 base (8)
  tabela de ponteiros u32 (offset relativo a 'base'), varios apontam pro mesmo texto
  pool: textos UTF-16LE terminados em 0 (2 bytes), um atras do outro

COMO USAR
  1) MODO = "extrair"      -> cria o CSV (abre no Excel/LibreOffice, separador ';')
  2) preencha a coluna "traducao" (vazio = mantem o original)
  3) MODO = "reconstruir"  -> le o CSV e cria o GameText_novo.l

No CSV, quebra de linha real aparece como <LF> (nao apague!).
Mantenha os codigos %d, %s, %02d etc. exatamente como no original.
"""
import csv
import os
import re
import struct
import sys
import unicodedata
from collections import Counter

MODO = "reconstruir"   # "extrair" ou "reconstruir"  (ou passe como argumento)

BASE = r"C:\Users\pache\OneDrive\Área de Trabalho\extrair video"
GAMETEXT = BASE + r"\US_nomeado\US\GameText\GameText.l"
FONTDB = BASE + r"\US_nomeado\US\Font\FontDatabase.l"      # usado so pra avisar de letras sem glifo
CSV_ARQ = BASE + r"\GameText_traducao.csv"
NOVO = BASE + r"\GameText_novo.l"

REUSAR_TRADUCAO_IGUAL = True   # linha sem traducao reaproveita a de outra linha com texto original igual
SEM_ACENTO_FALTANTE = True    # True = troca letras sem glifo na fonte pela letra sem acento (a->a, ã->a...)
                               # util pra TESTAR no jogo enquanto a fonte nao tem esses acentos

if len(sys.argv) > 1:
    MODO = sys.argv[1]

TOKENS = [("\r", "<CR>"), ("\t", "<TAB>"), ("\n", "<LF>")]
RE_PRINTF = re.compile(r"%[0-9.\-+ #]*[a-zA-Z]")
RE_INGLES = re.compile(r"[A-Za-z]{3,}")


def escapar(t):
    for real, tok in TOKENS:
        t = t.replace(real, tok)
    return t


def desescapar(t):
    for real, tok in TOKENS:
        t = t.replace(tok, real)
    return t


def ler_gametext(dados):
    n, base = struct.unpack_from("<II", dados, 0)
    ptrs = list(struct.unpack_from("<%dI" % n, dados, 8))
    ini = 8 + 4 * n
    segs = []          # (offset_no_arquivo, texto)
    p = ini
    while p < len(dados):
        e = p
        while e + 1 < len(dados) and dados[e:e + 2] != b"\0\0":
            e += 2
        if e + 1 >= len(dados):
            raise SystemExit("ERRO: texto sem terminador no fim do arquivo.")
        segs.append((p, dados[p:e].decode("utf-16le")))
        p = e + 2
    idx_por_off = {o: i for i, (o, _) in enumerate(segs)}
    destino = []       # ponteiro k -> indice do segmento
    for x in ptrs:
        if base + x not in idx_por_off:
            raise SystemExit("ERRO: ponteiro nao aponta pro inicio de um texto.")
        destino.append(idx_por_off[base + x])
    return n, base, ptrs, segs, destino


def montar_gametext(n, base, destino, textos):
    ini = 8 + 4 * n
    pos = ini
    off_seg = []
    pool = bytearray()
    for t in textos:
        off_seg.append(pos)
        b = t.encode("utf-16le") + b"\0\0"
        pool += b
        pos += len(b)
    tabela = struct.pack("<%dI" % n, *[off_seg[i] - base for i in destino])
    return struct.pack("<II", n, base) + tabela + bytes(pool)


def sem_acento(ch):
    base = unicodedata.normalize("NFD", ch)[0]
    return base


def carregar_glifos():
    if not os.path.exists(FONTDB):
        return None
    d = open(FONTDB, "rb").read()
    n = struct.unpack_from("<H", d, 0)[0]
    return {struct.unpack_from("<H", d, 8 + 8 * i)[0] for i in range(n)}


def extrair():
    dados = open(GAMETEXT, "rb").read()
    n, base, ptrs, segs, destino = ler_gametext(dados)
    usos = Counter(destino)
    with open(CSV_ARQ, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "usos", "ingles", "original", "traducao"])
        for i, (_, t) in enumerate(segs):
            t2 = escapar(t)
            assert "<LF>" not in t and "<CR>" not in t and "<TAB>" not in t
            w.writerow([i, usos.get(i, 0), "sim" if RE_INGLES.search(t) else "nao", t2, ""])
    print("Ponteiros:", n, "| textos (linhas do CSV):", len(segs))
    print("Textos com ingles:", sum(1 for _, t in segs if RE_INGLES.search(t)))
    print("CSV criado em:", CSV_ARQ)
    print("Preencha a coluna 'traducao'. Tip: filtre ingles = sim.")


def reconstruir():
    dados = open(GAMETEXT, "rb").read()
    n, base, ptrs, segs, destino = ler_gametext(dados)

    trad = {}
    with open(CSV_ARQ, newline="", encoding="utf-8-sig") as f:
        for lin in csv.DictReader(f, delimiter=";"):
            trad[int(lin["id"])] = (lin["original"], lin["traducao"])

    if len(trad) != len(segs):
        raise SystemExit("ERRO: o CSV tem %d linhas e o arquivo tem %d textos. "
                         "Nao apague/reordene linhas." % (len(trad), len(segs)))

    por_original = {}
    for i, (orig, tr) in trad.items():
        if tr != "" and orig not in por_original:
            por_original[orig] = tr

    textos, avisos = [], []
    traduzidos = reaproveitados = 0
    glifos = carregar_glifos()
    sem_glifo = Counter()
    for i, (_, original) in enumerate(segs):
        orig_csv, tr = trad[i]
        if orig_csv != escapar(original):
            raise SystemExit("ERRO: a coluna 'original' da linha id=%d foi alterada. "
                             "Use so a coluna 'traducao'." % i)
        if tr == "" and REUSAR_TRADUCAO_IGUAL and orig_csv in por_original:
            tr = por_original[orig_csv]
            reaproveitados += 1
        elif tr != "":
            traduzidos += 1
        if tr == "":
            textos.append(original)
            continue
        novo = desescapar(tr)
        if SEM_ACENTO_FALTANTE and glifos is not None:
            novo = "".join(c if (ord(c) < 0x20 or ord(c) in glifos) else sem_acento(c) for c in novo)
        textos.append(novo)
        if Counter(RE_PRINTF.findall(novo)) != Counter(RE_PRINTF.findall(original)):
            avisos.append("id %d: codigos %% diferentes do original: %r" % (i, orig_csv[:50]))
        if len(novo) > 1.5 * len(original) + 8:
            avisos.append("id %d: bem mais longo que o original (pode estourar a caixa): %r" % (i, tr[:50]))
        if glifos is not None:
            for ch in set(novo):
                if ord(ch) >= 0x20 and ord(ch) not in glifos:
                    sem_glifo[ch] += 1

    novo_bytes = montar_gametext(n, base, destino, textos)
    open(NOVO, "wb").write(novo_bytes)

    # confere o arquivo gerado lendo de volta
    n2, base2, _, segs2, destino2 = ler_gametext(novo_bytes)
    assert n2 == n and base2 == base and destino2 == destino
    assert [t for _, t in segs2] == textos

    print("Linhas traduzidas:", traduzidos, "| reaproveitadas (original igual):", reaproveitados)
    print("Arquivo criado:", NOVO, "(%d bytes; original %d)" % (len(novo_bytes), len(dados)))
    if novo_bytes == dados:
        print("(Sem traducoes: o arquivo e identico ao original.)")
    if glifos is None:
        print("(FontDatabase.l nao encontrado: pulei a checagem de letras sem glifo.)")
    elif sem_glifo:
        print("ATENCAO - letras SEM glifo na fonte do jogo (vao aparecer erradas):")
        print("  " + ", ".join("%s (%d linhas)" % (c, k) for c, k in sorted(sem_glifo.items())))
    for a in avisos[:40]:
        print("AVISO:", a)
    if len(avisos) > 40:
        print("... e mais", len(avisos) - 40, "avisos")


if MODO == "extrair":
    extrair()
elif MODO == "reconstruir":
    reconstruir()
else:
    print('MODO deve ser "extrair" ou "reconstruir"')