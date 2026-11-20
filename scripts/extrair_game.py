CAMINHO = r"C:\Program Files (x86)\Steam\steamapps\common\Way of the Samurai 3\US.bra"
SAIDA = r"C:\Users\pache\OneDrive\Área de Trabalho\extrair video\amostra.bin"

import os
print("Tamanho total:", os.path.getsize(CAMINHO), "bytes")
with open(CAMINHO, "rb") as f:
    dados = f.read(2 * 1024 * 1024)   # primeiros 2 MB
with open(SAIDA, "wb") as f:
    f.write(dados)
print("Pronto! amostra.bin criado.")