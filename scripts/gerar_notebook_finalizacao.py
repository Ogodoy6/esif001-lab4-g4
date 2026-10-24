"""Gera notebooks/Lab4.6_Finalizacao_Avaliacoes_G4.ipynb (executar uma vez localmente)."""
import json, sys
from pathlib import Path

def md(s): return {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}
def code(s): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n").splitlines(True)}

cells = [
md("""
# Lab4.6 — Finalização das avaliações cruzadas (G4 ↔ G3)

Este notebook complementa o Lab4.4 e o Lab4.5. Ele reúne em um só lugar o que **ainda falta** para o G4:

| Etapa | Quem executa | O que faz |
|---|---|---|
| 0 | qualquer integrante | monta o Drive e mostra o que já existe em `Lab4_CSM/G3` e `Lab4_CSM/G4` |
| 1 | G4 (produtor) | gera o pacote de **imagens** do G4 para o G3 (o pacote de áudio já foi gerado em 16/10) |
| 2 | cada integrante do G4 (A1–A4) | avalia o **áudio** do G3 (MUSHRA-like, 0–100) |
| 3 | cada integrante do G4 (A1–A4) | avalia as **imagens** do G3 (diferença 0–3) |
| 4 | G4 (produtor) | junta as notas que o G3 deu ao G4 com os gabaritos privados e exporta os resumos para o site |

**Pré-requisito:** as pastas `G3/` e `G4/` devem estar dentro da mesma `MyDrive/Lab4_CSM/` (enunciado, item 3e). Se o G3 trabalhou em outro Drive, peça que ele copie `G3/pacote_audio/` e `G3/pacote_imagem/` para `MyDrive/Lab4_CSM/G3/` nesta conta, e que devolva os CSVs de notas para `G4/audio/resultados_recebidos/` e `G4/imagens/resultados_recebidos/`.

O G3 avalia o material do G4 executando as seções 2 e 3 **com `MEU_GRUPO = 'G3'`**.
"""),
md("## 0. Configuração e diagnóstico"),
code("""
from pathlib import Path
import json, random, shutil, subprocess
import pandas as pd
from google.colab import drive

# Montagem robusta: na execução anterior do Lab4.5 a montagem falhou por timeout.
try:
    drive.mount('/content/drive')
except ValueError:
    drive.mount('/content/drive', force_remount=True)

MEU_GRUPO = 'G4'     # grupo de quem está executando (G3 usa 'G3')
AVALIADOR = 'A1'     # A1, A2, A3 ou A4 — cada integrante muda e executa de novo as seções 2 e 3
PARES = {'G1':'G2','G2':'G1','G3':'G4','G4':'G3','G5':'G6','G6':'G5'}
PARCEIRO = PARES[MEU_GRUPO]
RAIZ = Path('/content/drive/MyDrive/Lab4_CSM')
assert RAIZ.is_dir(), f'Pasta não encontrada: {RAIZ}'
assert AVALIADOR in ('A1','A2','A3','A4')

def status(g):
    p = RAIZ / g
    itens = {
        'audio/referencia.wav': (p/'audio'/'referencia.wav').is_file(),
        'pacote_audio (6 estímulos)': len(list((p/'pacote_audio').glob('S*.wav'))) == 6,
        'audio/gabarito_audio_PRIVADO.csv': (p/'audio'/'gabarito_audio_PRIVADO.csv').is_file(),
        'imagens/medidas_imagem.csv': (p/'imagens'/'medidas_imagem.csv').is_file(),
        'pacote_imagem (3 pares)': len(list((p/'pacote_imagem').glob('P*_A.png'))) == 3,
        'imagens/gabarito_imagem_PRIVADO.csv': (p/'imagens'/'gabarito_imagem_PRIVADO.csv').is_file(),
        'CSVs recebidos (áudio)': len(list((p/'audio'/'resultados_recebidos').glob('*.csv'))),
        'CSVs recebidos (imagem)': len(list((p/'imagens'/'resultados_recebidos').glob('*.csv'))),
    }
    print(f'--- {g} ---')
    for k, v in itens.items():
        print(f'  {"OK " if v else "-- "} {k}: {v}')

for g in (MEU_GRUPO, PARCEIRO):
    status(g)
"""),
md("""
## 1. Produtor — gerar o pacote de imagens

Executar **uma vez**, no grupo produtor (`MEU_GRUPO`). Escolhe uma imagem original e cria três pares original × JPEG (`q:v` 2, 20, 31) com lado A/B e ordem aleatórios. O gabarito fica em `imagens/gabarito_imagem_PRIVADO.csv` e **não** deve ser mostrado ao parceiro.

Para o G4 a imagem sugerida é `G4_1792112691.png` (a de maior arquivo PNG, ou seja, com mais detalhes e textura entre as sete capturas).
"""),
code("""
from PIL import Image
NOME_IMAGEM = 'G4_1792112691.png' if MEU_GRUPO == 'G4' else 'ALTERAR.png'

def preparar_imagens(grupo=MEU_GRUPO, nome=NOME_IMAGEM):
    base = RAIZ / grupo / 'imagens'
    original = base / 'originais' / nome
    assert original.is_file(), f'Original não encontrado: {original}'
    entradas = [(q, base / 'jpeg' / f'{original.stem}_q{q}.jpg') for q in (2, 20, 31)]
    falt = [str(a) for _, a in entradas if not a.is_file()]
    assert not falt, 'JPEGs ausentes (execute o Lab4.3):\\n' + '\\n'.join(falt)
    pacote = RAIZ / grupo / 'pacote_imagem'
    pacote.mkdir(parents=True, exist_ok=True)
    for f in pacote.glob('P*_*.png'): f.unlink()
    rnd = random.SystemRandom(); rnd.shuffle(entradas)
    ref = Image.open(original).convert('RGB')
    chave = []
    for i, (q, arq) in enumerate(entradas, 1):
        teste = Image.open(arq).convert('RGB')
        assert ref.size == teste.size, f'Dimensões diferentes: {arq}'
        pid, lado = f'P{i:02d}', rnd.choice('AB')
        a, b = (ref, teste) if lado == 'A' else (teste, ref)
        a.save(pacote / f'{pid}_A.png'); b.save(pacote / f'{pid}_B.png')
        chave.append({'par': pid, 'q_ffmpeg': q, 'original_lado': lado})
    pd.DataFrame(chave).to_csv(base / 'gabarito_imagem_PRIVADO.csv', index=False)
    (pacote / 'info.json').write_text(json.dumps({'produtor': grupo, 'avaliador': PARES[grupo],
        'imagem_original': original.name}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Pacote pronto em', pacote, '| imagem:', original.name)

# Retire o # para gerar (sobrescreve um pacote existente):
# preparar_imagens()
"""),
md("""
## 2. Avaliador — áudio do parceiro (MUSHRA-like, 0–100)

Use fones, volume confortável, ambiente silencioso. Ouça primeiro a **referência identificada** (não recebe nota). Entre os seis estímulos estão uma **referência oculta** (deveria receber ~100) e uma **âncora** passa-baixas em 3,5 kHz (deveria receber nota baixa). Escala: 0–20 ruim · 20–40 pobre · 40–60 razoável · 60–80 boa · 80–100 excelente.

Ao salvar, o CSV vai para `MEU_GRUPO/avaliacoes_audio/` **e** é copiado para `PARCEIRO/audio/resultados_recebidos/`.
"""),
code("""
from IPython.display import Audio, display, HTML
import ipywidgets as w
origem = RAIZ / PARCEIRO / 'pacote_audio'
assert (origem / 'referencia_identificada.wav').is_file(), f'Pacote de áudio do {PARCEIRO} não encontrado em {origem}'
estimulos = sorted(origem.glob('S*.wav')); assert len(estimulos) == 6
display(HTML(f'<h3>{MEU_GRUPO}/{AVALIADOR} avalia o áudio de {PARCEIRO}</h3><b>Referência identificada (sem nota)</b>'))
display(Audio(filename=str(origem / 'referencia_identificada.wav')))
ctrl_a = []
for p in estimulos:
    s = w.IntSlider(value=50, min=0, max=100, description=p.stem, continuous_update=False)
    obs = w.Text(placeholder='artefatos percebidos (opcional)', layout=w.Layout(width='60%'))
    display(HTML(f'<b>{p.stem}</b>'), Audio(filename=str(p)), w.HBox([s, obs]))
    ctrl_a.append((p, s, obs))
bt_a, out_a = w.Button(description='Salvar notas de áudio', button_style='success'), w.Output()
def salvar_audio(_):
    with out_a:
        out_a.clear_output()
        df = pd.DataFrame([{'grupo_avaliador': MEU_GRUPO, 'grupo_produtor': PARCEIRO, 'avaliador': AVALIADOR,
                            'estimulo': p.name, 'nota_0_100': s.value, 'observacao': o.value} for p, s, o in ctrl_a])
        d1 = RAIZ / MEU_GRUPO / 'avaliacoes_audio'; d2 = RAIZ / PARCEIRO / 'audio' / 'resultados_recebidos'
        d1.mkdir(parents=True, exist_ok=True); d2.mkdir(parents=True, exist_ok=True)
        df.to_csv(d1 / f'{PARCEIRO}_{AVALIADOR}.csv', index=False)
        df.to_csv(d2 / f'{MEU_GRUPO}_{AVALIADOR}.csv', index=False)
        print('Salvo e entregue ao produtor:', d2 / f'{MEU_GRUPO}_{AVALIADOR}.csv')
bt_a.on_click(salvar_audio); display(bt_a, out_a)
"""),
md("""
## 3. Avaliador — imagens do parceiro (diferença percebida 0–3)

Compare A e B em cada par. **0** = imperceptível · **1** = discreta · **2** = evidente · **3** = muito evidente. A nota não é preferência A/B. Observe áreas uniformes (céu, parede), bordas e texturas; use o zoom do navegador se precisar.
"""),
code("""
pac = RAIZ / PARCEIRO / 'pacote_imagem'
assert (pac / 'info.json').is_file(), f'Pacote de imagens do {PARCEIRO} não encontrado em {pac}'
info = json.loads((pac / 'info.json').read_text(encoding='utf-8'))
display(HTML(f'<h3>{MEU_GRUPO}/{AVALIADOR} avalia as imagens de {PARCEIRO}</h3>'))
ctrl_i = []
for i in range(1, 4):
    pid = f'P{i:02d}'
    a, b = pac / f'{pid}_A.png', pac / f'{pid}_B.png'
    display(w.HBox([w.VBox([w.Label(f'{pid} — A'), w.Image(value=a.read_bytes(), format='png', width=420)]),
                    w.VBox([w.Label(f'{pid} — B'), w.Image(value=b.read_bytes(), format='png', width=420)])]))
    s = w.IntSlider(value=0, min=0, max=3, description=pid, continuous_update=False)
    obs = w.Text(placeholder='onde aparece a diferença? (bordas, textura, área lisa)', layout=w.Layout(width='60%'))
    display(w.HBox([s, obs])); ctrl_i.append((pid, s, obs))
bt_i, out_i = w.Button(description='Salvar notas de imagem', button_style='success'), w.Output()
def salvar_img(_):
    with out_i:
        out_i.clear_output()
        df = pd.DataFrame([{'grupo_avaliador': MEU_GRUPO, 'grupo_produtor': PARCEIRO, 'avaliador': AVALIADOR,
                            'imagem_original': info.get('imagem_original', ''), 'par': pid,
                            'diferenca_0_3': s.value, 'observacao': o.value} for pid, s, o in ctrl_i])
        d1 = RAIZ / MEU_GRUPO / 'avaliacoes_imagem'; d2 = RAIZ / PARCEIRO / 'imagens' / 'resultados_recebidos'
        d1.mkdir(parents=True, exist_ok=True); d2.mkdir(parents=True, exist_ok=True)
        df.to_csv(d1 / f'{PARCEIRO}_{AVALIADOR}.csv', index=False)
        df.to_csv(d2 / f'{MEU_GRUPO}_{AVALIADOR}.csv', index=False)
        print('Salvo e entregue ao produtor:', d2 / f'{MEU_GRUPO}_{AVALIADOR}.csv')
bt_i.on_click(salvar_img); display(bt_i, out_i)
"""),
md("""
## 4. Produtor — interpretar as notas recebidas

Executar **só depois** que todos os avaliadores do parceiro terminarem. Junta notas e gabaritos e grava `resumo_audio.csv`, `resumo_imagem.csv`, `notas_audio_completas.csv` e `notas_imagem_completas.csv` em `MEU_GRUPO/resultados/`. Copie esses CSVs para a pasta `dados/` do repositório e execute `scripts/analise.py` para atualizar figuras e tabelas do site.
"""),
code("""
P = RAIZ / MEU_GRUPO; saida = P / 'resultados'; saida.mkdir(exist_ok=True)
med_a = pd.read_csv(P/'audio'/'medidas_audio.csv')
med_a['condicao'] = med_a['arquivo'].str.rsplit('.', n=1).str[0]

rec_a = sorted((P/'audio'/'resultados_recebidos').glob('*.csv'))
if rec_a:
    notas = pd.concat([pd.read_csv(f) for f in rec_a], ignore_index=True)
    gab = pd.read_csv(P/'audio'/'gabarito_audio_PRIVADO.csv')
    ra = notas.merge(gab, left_on='estimulo', right_on='codigo', how='left')
    ra.to_csv(saida/'notas_audio_completas.csv', index=False)
    res = (ra.groupby('condicao')['nota_0_100'].agg(n='count', media='mean', dp='std', minimo='min', maximo='max')
             .reset_index().merge(med_a[['condicao','codec','kbps_nominal','kbps_efetivo','bytes']], on='condicao', how='left')
             .sort_values('media', ascending=False))
    res.to_csv(saida/'resumo_audio.csv', index=False); display(res.round(1))
    display(ra.pivot_table(index='avaliador', columns='condicao', values='nota_0_100'))
    ok = ra.query("condicao=='REF_OCULTA'")['nota_0_100']
    print('Avaliadores que deram < 90 à referência oculta (critério de triagem MUSHRA):',
          list(ra.loc[ok[ok < 90].index, 'avaliador']))
else:
    print('Nenhuma nota de áudio recebida ainda.')

med_i = pd.read_csv(P/'imagens'/'medidas_imagem.csv')
rec_i = sorted((P/'imagens'/'resultados_recebidos').glob('*.csv'))
gab_i = P/'imagens'/'gabarito_imagem_PRIVADO.csv'
if rec_i and gab_i.is_file():
    notas_i = pd.concat([pd.read_csv(f) for f in rec_i], ignore_index=True)
    ri = notas_i.merge(pd.read_csv(gab_i), on='par', how='left')
    ri = ri.merge(med_i[['imagem','q_ffmpeg','bytes_jpeg','reducao_pct']],
                  left_on=['imagem_original','q_ffmpeg'], right_on=['imagem','q_ffmpeg'], how='left')
    ri.to_csv(saida/'notas_imagem_completas.csv', index=False)
    resi = (ri.groupby('q_ffmpeg').agg(n=('diferenca_0_3','count'), media=('diferenca_0_3','mean'),
            dp=('diferenca_0_3','std'), reducao_pct=('reducao_pct','first')).reset_index())
    resi.to_csv(saida/'resumo_imagem.csv', index=False); display(resi.round(2))
else:
    print('Nenhuma nota de imagem recebida ainda (ou gabarito de imagem ausente).')
print('Arquivos em', saida, ':', [f.name for f in saida.iterdir()])
"""),
]

nb = {"cells": cells, "metadata": {"colab": {"provenance": []},
      "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
      "nbformat": 4, "nbformat_minor": 5}
out = Path(sys.argv[1] if len(sys.argv) > 1 else 'notebooks/Lab4.6_Finalizacao_Avaliacoes_G4.ipynb')
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('ok', out)
