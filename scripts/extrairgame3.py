CAMINHO = r"C:\Program Files (x86)\Steam\steamapps\common\Way of the Samurai 3\US.bra"
SAIDA = r"C:\Users\pache\OneDrive\Área de Trabalho\extrair video\cauda.bin"

with open(CAMINHO, "rb") as f:
    f.seek(340536114)
    dados = f.read()
with open(SAIDA, "wb") as f:
    f.write(dados)
print("Bytes salvos:", len(dados))