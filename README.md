# ESIF001 — Lab 4: Codificação com Perdas de Áudio e Imagem (G4)

Codificação de áudio (MP3, AAC e Ogg Vorbis, a 48 e 128 kbit/s) e de imagem (JPEG com `-q:v` 2, 20 e 31), com medidas objetivas e avaliação perceptiva cruzada com o grupo G3.

📄 **Relatório completo:** [RELATORIO.md](RELATORIO.md)

## Resultados principais

| Áudio (8,3 s, 44,1 kHz estéreo) | 48 kbit/s | 128 kbit/s |
|---|---|---|
| Redução vs WAV (1 411 kbit/s) | ≈ 96,5 % (29 : 1) | ≈ 91 % (11 : 1) |
| Banda preservada | MP3/AAC ≈ 7,7 kHz · Vorbis ≈ 14 kHz | 16–18 kHz |

| Imagem (7 capturas 640 × 480) | q:v 2 | q:v 20 | q:v 31 |
|---|---:|---:|---:|
| Redução vs PNG | 79,1 % | 95,4 % | 96,2 % |
| PSNR médio | 41,4 dB | 30,7 dB | 28,9 dB |
| SSIM médio | 0,977 | 0,878 | 0,848 |

## Estrutura

```
notebooks/   Lab4.1 a Lab4.5 (configurados para o G4) e Lab4.6 (finalização das avaliações G3↔G4)
dados/       medidas_audio.csv, medidas_imagem.csv (gerados nos notebooks)
             metricas_audio.csv, metricas_imagem.csv, resumo_metricas_imagem.csv,
             erro_por_regiao_*.csv (gerados por scripts/analise.py)
             notas_*_completas.csv, resumo_audio.csv, resumo_imagem.csv (notas da avaliação)
figuras/     espectros, espectrogramas, tamanho x taxa, redução/PSNR, recortes de artefatos JPEG
scripts/     analise.py (métricas e figuras); simular_avaliacao_G3.py; gerar_notebook_finalizacao.py
```

## Como reproduzir

1. Execute os notebooks Lab4.1 → Lab4.5 no Google Colab, com a pasta `MyDrive/Lab4_CSM/G4/`.
2. Baixe a pasta `G4` do Drive e rode:
   ```bash
   pip install -r requirements.txt   # requer também o FFmpeg no PATH
   python scripts/analise.py --midia caminho/para/G4
   ```
3. Depois das avaliações, copie para `dados/` os CSVs gerados pela seção 4 do Lab4.6. Rode `python scripts/analise.py` de novo para gerar `figuras/notas_*.png`.

## Privacidade

As fotografias mostram integrantes da turma, e as gravações são de voz/sala. Por isso, **não** estão neste repositório público, conforme o item 9e do roteiro. Elas permanecem no Google Drive da disciplina. As figuras publicadas são apenas recortes sem rostos (livro, camiseta, pelúcia) e gráficos. Os gabaritos privados também ficam fora do repositório até o encerramento das avaliações.

## Avaliação subjetiva

Como o G3 não realizou a avaliação cruzada, as notas foram obtidas por simulação (`scripts/simular_avaliacao_G3.py`), conforme orientação do professor.
