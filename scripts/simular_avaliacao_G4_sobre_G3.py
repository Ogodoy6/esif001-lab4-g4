"""SIMULAÇÃO da avaliação dos pacotes do G3 pelos integrantes do G4 (seções 3.3 e 4.4).

O G3 não disponibilizou G3/pacote_audio nem G3/pacote_imagem. Conforme orientação do
professor ("Caso o grupo não contribua, faça um resultado simulado"), este script gera
notas SIMULADAS para os 4 avaliadores do G4 (A1–A4). Toda linha traz origem = 'SIMULADO'.
Isto NÃO são notas de pessoas, e os pacotes do G3 também são hipotéticos.

Hipóteses sobre os pacotes do G3 (não conhecemos os arquivos reais):
  Áudio  — mesma estrutura do roteiro (referência oculta, âncora LP 3,5 kHz e 4 versões
           codificadas). Supusemos as 4 versões AAC 128k, Vorbis 128k, Vorbis 48k e MP3 48k,
           ou seja, uma combinação diferente da do G4, cobrindo os três codecs.
           Como o material do G3 também é uma gravação do Lab 3 com os mesmos codecs e taxas,
           usamos como aproximação a banda medida nas versões do G4 (dados/metricas_audio.csv).
  Imagem — uma captura de webcam 640 × 480 comprimida com q 2, 20 e 31. Usamos como
           aproximação o SSIM MÉDIO das 7 imagens do G4 (dados/resumo_metricas_imagem.csv).

Modelos (os mesmos das seções 3.2 e 4.3):
  Áudio  : nota esperada = 25 + (banda_kHz − 3,5) × 72/14,6
           penalidade −10 para versões a 48 kbit/s com artefato visível no espectrograma
           (MP3 48k: buracos espectrais; Vorbis 48k: ruído granulado entre 10 e 14 kHz)
           nota = esperada + viés do avaliador N(0, 5) + ruído N(0, 7), limitada a 0–100
  Imagem : esperado = 3 × min(1, (1 − SSIM)/0,2) × 0,7
           nota = arredonda(esperado + N(0, 0,5)), limitada a 0–3
Semente fixa 3434 (diferente da usada para o G3 avaliar o G4) → resultado reprodutível.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
D, FIG = RAIZ / 'dados', RAIZ / 'figuras'
rng = np.random.default_rng(3434)
AVAL = ['A1', 'A2', 'A3', 'A4']
plt.rcParams.update({'figure.dpi': 130, 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False})

# ---------- áudio (3.3) ----------
gab = pd.DataFrame({'codigo': [f'S0{i}.wav' for i in range(1, 7)]})
gab['condicao'] = rng.permutation(['REF_OCULTA', 'ANCORA', 'aac_128k', 'vorbis_128k', 'vorbis_48k', 'mp3_48k'])
met = pd.read_csv(D / 'metricas_audio.csv')
banda = {r.arquivo.rsplit('.', 1)[0]: r.banda_ate_kHz for r in met.itertuples()}
banda.update({'REF_OCULTA': 18.1, 'ANCORA': 3.5})
esperado = {c: 25 + (b - 3.5) * 72 / 14.6 for c, b in banda.items()}
esperado['mp3_48k'] -= 10
esperado['vorbis_48k'] -= 10
vies = dict(zip(AVAL, rng.normal(0, 5, 4)))
linhas = []
for a in AVAL:
    for r in gab.itertuples():
        nota = int(np.clip(round(esperado[r.condicao] + vies[a] + rng.normal(0, 7)), 0, 100))
        linhas.append({'grupo_avaliador': 'G4', 'grupo_produtor': 'G3', 'avaliador': a, 'estimulo': r.codigo,
                       'nota_0_100': nota, 'condicao': r.condicao, 'banda_kHz_aprox': banda[r.condicao],
                       'nota_esperada_modelo': round(esperado[r.condicao], 1), 'origem': 'SIMULADO'})
na = pd.DataFrame(linhas)
na.to_csv(D / 'notas_audio_G4_avalia_G3_SIMULADO.csv', index=False)
ra = (na.groupby('condicao').agg(banda=('banda_kHz_aprox', 'first'), esperado=('nota_esperada_modelo', 'first'),
                                 n=('nota_0_100', 'count'), media=('nota_0_100', 'mean'), dp=('nota_0_100', 'std'),
                                 minimo=('nota_0_100', 'min'), maximo=('nota_0_100', 'max'))
        .sort_values('media', ascending=False).round(1))
ra.to_csv(D / 'resumo_audio_G4_avalia_G3_SIMULADO.csv')

ordem = list(ra.index)
fig, ax = plt.subplots(figsize=(6, 3.2))
ax.boxplot([na[na.condicao == c].nota_0_100 for c in ordem])
ax.set_xticks(range(1, len(ordem) + 1), ordem)
for i, c in enumerate(ordem, 1):
    ax.scatter(np.full((na.condicao == c).sum(), i), na[na.condicao == c].nota_0_100, s=12, color='#e07b39', zorder=3)
ax.set(ylim=(0, 100), ylabel='Nota (0–100)', title='SIMULADO — notas do G4 para o pacote de áudio do G3')
plt.setp(ax.get_xticklabels(), rotation=20); fig.tight_layout()
fig.savefig(FIG / 'notas_audio_G4_avalia_G3_SIMULADO.png'); plt.close(fig)

# ---------- imagem (4.4) ----------
rm = pd.read_csv(D / 'resumo_metricas_imagem.csv').set_index('q_ffmpeg')
pares = pd.DataFrame({'par': ['P01', 'P02', 'P03'], 'q_ffmpeg': rng.permutation([2, 20, 31]),
                      'original_lado': rng.choice(['A', 'B'], 3)})
linhas = []
for a in AVAL:
    for p in pares.itertuples():
        m = rm.loc[p.q_ffmpeg]
        esp = 3 * min(1, (1 - m.ssim) / 0.2) * 0.7
        nota = int(np.clip(round(esp + rng.normal(0, 0.5)), 0, 3))
        linhas.append({'grupo_avaliador': 'G4', 'grupo_produtor': 'G3', 'avaliador': a,
                       'imagem_original': 'G3_hipotetica.png', 'par': p.par, 'diferenca_0_3': nota,
                       'q_ffmpeg': p.q_ffmpeg, 'original_lado': p.original_lado,
                       'reducao_pct_aprox': round(m.reducao_media_pct, 2), 'ssim_aprox': m.ssim,
                       'nota_esperada_modelo': round(esp, 2), 'origem': 'SIMULADO'})
ni = pd.DataFrame(linhas)
ni.to_csv(D / 'notas_imagem_G4_avalia_G3_SIMULADO.csv', index=False)
ri = (ni.groupby('q_ffmpeg').agg(reducao_pct=('reducao_pct_aprox', 'first'), ssim=('ssim_aprox', 'first'),
      esperado=('nota_esperada_modelo', 'first'), n=('diferenca_0_3', 'count'),
      media=('diferenca_0_3', 'mean'), dp=('diferenca_0_3', 'std')).round(2))
ri.to_csv(D / 'resumo_imagem_G4_avalia_G3_SIMULADO.csv')

fig, ax = plt.subplots(figsize=(4.8, 3.2))
ax.scatter(ni.reducao_pct_aprox, ni.diferenca_0_3 + rng.uniform(-.06, .06, len(ni)), color='#e07b39')
ax.plot(ri.reducao_pct, ri.media, 'k-o')
ax.set(xlabel='Redução de dados (%)', ylabel='Diferença percebida (0–3)', ylim=(-0.3, 3.3),
       title='SIMULADO — pacote de imagens do G3')
fig.tight_layout(); fig.savefig(FIG / 'notas_imagem_G4_avalia_G3_SIMULADO.png'); plt.close(fig)

print('GABARITO ÁUDIO (hipotético)\n', gab.to_string(index=False))
print('\nÁUDIO (SIMULADO)\n', ra.to_string())
print('\nindividual\n', na.pivot(index='avaliador', columns='condicao', values='nota_0_100')[ordem].to_string())
print('\nPARES IMAGEM\n', pares.to_string(index=False))
print('\nIMAGEM (SIMULADO)\n', ri.to_string())
print('\nindividual\n', ni.pivot(index='avaliador', columns='q_ffmpeg', values='diferenca_0_3').to_string())
