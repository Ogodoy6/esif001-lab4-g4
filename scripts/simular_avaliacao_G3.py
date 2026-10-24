"""SIMULAÇÃO das notas do grupo parceiro (G3) para o pacote do G4.

O G3 não realizou a avaliação cruzada. Conforme o adendo do professor ("Caso o grupo
não contribua, faça um resultado simulado"), este script gera notas SIMULADAS para
4 avaliadores (A1–A4) a partir das medidas objetivas, com um modelo simples e
documentado. Toda linha gerada traz origem = 'SIMULADO'. Isto NÃO são notas de pessoas.

Modelo — áudio (MUSHRA-like, 0–100):
  nota esperada = 25 + (banda_kHz − 3,5) × 72/14,6   (reta que leva a âncora de 3,5 kHz a 25
                                                      e a referência de 18,1 kHz a 97)
  penalidade de −10 para MP3 48k (buracos espectrais visíveis no espectrograma)
  nota = esperada + viés do avaliador N(0, 5) + ruído N(0, 7), limitada a 0–100
Modelo — imagem (diferença percebida 0–3), imagem G4_1792112691.png:
  esperado = 3 × min(1, (1 − SSIM)/0,2) × 0,7       (0,7 = atenuação porque os pares são
                                                      exibidos reduzidos a ~360 px no Colab)
  nota = arredonda(esperado + N(0, 0,5)), limitada a 0–3
Semente fixa (2026) → resultado reprodutível.
"""
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
D = RAIZ / 'dados'
rng = np.random.default_rng(2026)
AVAL = ['A1', 'A2', 'A3', 'A4']

# ---------- áudio ----------
gab = pd.DataFrame({'codigo': [f'S0{i}.wav' for i in range(1, 7)],
                    'condicao': ['mp3_128k', 'ANCORA', 'vorbis_128k', 'mp3_48k', 'aac_48k', 'REF_OCULTA']})
met = pd.read_csv(D / 'metricas_audio.csv')
banda = {r.arquivo.rsplit('.', 1)[0]: r.banda_ate_kHz for r in met.itertuples()}
banda.update({'REF_OCULTA': 18.1, 'ANCORA': 3.5})
esperado = {c: 25 + (b - 3.5) * 72 / 14.6 for c, b in banda.items()}
esperado['mp3_48k'] -= 10
vies = dict(zip(AVAL, rng.normal(0, 5, 4)))
linhas = []
for a in AVAL:
    for r in gab.itertuples():
        nota = int(np.clip(round(esperado[r.condicao] + vies[a] + rng.normal(0, 7)), 0, 100))
        linhas.append({'grupo_avaliador': 'G3', 'grupo_produtor': 'G4', 'avaliador': a, 'estimulo': r.codigo,
                       'nota_0_100': nota, 'codigo': r.codigo, 'condicao': r.condicao,
                       'nota_esperada_modelo': round(esperado[r.condicao], 1), 'origem': 'SIMULADO'})
na = pd.DataFrame(linhas)
na.to_csv(D / 'notas_audio_completas.csv', index=False)

# ---------- imagem ----------
mi = pd.read_csv(D / 'metricas_imagem.csv').query("imagem == 'G4_1792112691.png'")
ordem = rng.permutation([2, 20, 31])
pares = pd.DataFrame({'par': ['P01', 'P02', 'P03'], 'q_ffmpeg': ordem,
                      'original_lado': rng.choice(['A', 'B'], 3)})
linhas = []
for a in AVAL:
    for p in pares.itertuples():
        m = mi[mi.q_ffmpeg == p.q_ffmpeg].iloc[0]
        esp = 3 * min(1, (1 - m.ssim) / 0.2) * 0.7
        nota = int(np.clip(round(esp + rng.normal(0, 0.5)), 0, 3))
        linhas.append({'grupo_avaliador': 'G3', 'grupo_produtor': 'G4', 'avaliador': a,
                       'imagem_original': 'G4_1792112691.png', 'par': p.par, 'diferenca_0_3': nota,
                       'q_ffmpeg': p.q_ffmpeg, 'original_lado': p.original_lado,
                       'reducao_pct': m.reducao_pct, 'ssim': m.ssim,
                       'nota_esperada_modelo': round(esp, 2), 'origem': 'SIMULADO'})
ni = pd.DataFrame(linhas)
ni.to_csv(D / 'notas_imagem_completas.csv', index=False)

# ---------- resumos ----------
ra = (na.groupby('condicao').nota_0_100.agg(n='count', media='mean', dp='std', minimo='min', maximo='max')
        .sort_values('media', ascending=False).round(1))
ra.to_csv(D / 'resumo_audio.csv')
ri = (ni.groupby('q_ffmpeg').agg(reducao_pct=('reducao_pct', 'first'), n=('diferenca_0_3', 'count'),
      media=('diferenca_0_3', 'mean'), dp=('diferenca_0_3', 'std')).round(2))
ri.to_csv(D / 'resumo_imagem.csv')
print('ÁUDIO (SIMULADO)\n', ra.to_string())
print('\nindividual\n', na.pivot(index='avaliador', columns='condicao', values='nota_0_100').to_string())
print('\nIMAGEM (SIMULADO)\n', ri.to_string())
print('\nindividual\n', ni.pivot(index='avaliador', columns='q_ffmpeg', values='diferenca_0_3').to_string())
