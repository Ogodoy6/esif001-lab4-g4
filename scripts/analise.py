"""Análise objetiva do Lab 4 (G4): áudio e imagem.

Uso:
    python scripts/analise.py --midia CAMINHO/PARA/Lab4_CSM/G4

Lê dados/medidas_*.csv e, se --midia for informado, os arquivos de áudio/imagem
para calcular métricas objetivas e gerar figuras em figuras/.
Se existirem dados/notas_audio_completas.csv e dados/notas_imagem_completas.csv
(exportados pelo notebook Lab4.6), gera também os gráficos de notas x redução.
"""
import argparse, subprocess, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy import signal
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr, structural_similarity as ssim

RAIZ = Path(__file__).resolve().parents[1]
DADOS, FIG = RAIZ / 'dados', RAIZ / 'figuras'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'figure.dpi': 130, 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False})
COR = {'MP3': '#2a6fdb', 'AAC': '#e07b39', 'Vorbis': '#3a9d5d'}


def decodificar(arq, sr=44100):
    with tempfile.NamedTemporaryFile(suffix='.wav') as t:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(arq), '-ar', str(sr), '-ac', '2',
                        '-c:a', 'pcm_s16le', t.name], check=True)
        _, x = wavfile.read(t.name)
    return x.astype(np.float64).mean(axis=1) / 32768


def alinhar(ref, x):
    """Compensa o atraso do codificador (priming) por correlação cruzada."""
    n = min(len(ref), len(x), 44100 * 3)
    c = signal.correlate(x[:n], ref[:n], mode='full', method='fft')
    atraso = int(np.argmax(c) - (n - 1))
    x = x[atraso:] if atraso > 0 else np.concatenate([np.zeros(-atraso), x])
    m = min(len(ref), len(x))
    return ref[:m], x[:m], atraso


def corte_banda(x, sr=44100, limiar_db=-60):
    """Frequência acima da qual a PSD média fica abaixo de limiar_db (relativo ao pico)."""
    f, p = signal.welch(x, sr, nperseg=4096)
    pdb = 10 * np.log10(p + 1e-20); pdb -= pdb.max()
    acima = np.where(pdb > limiar_db)[0]
    return f[acima[-1]] if len(acima) else 0.0, f, pdb


def audio(midia):
    med = pd.read_csv(DADOS / 'medidas_audio.csv')
    sr, refi = wavfile.read(midia / 'audio' / 'referencia.wav')
    ref = refi.astype(np.float64).mean(axis=1) / 32768
    dur = len(ref) / sr
    bytes_wav = (midia / 'audio' / 'referencia.wav').stat().st_size
    linhas, espectros = [], {}
    fc_ref, f, pref = corte_banda(ref, sr)
    espectros['Referência WAV'] = pref
    for _, r in med.iterrows():
        x = decodificar(midia / 'audio' / 'codificados' / r['arquivo'])
        a, b, atraso = alinhar(ref, x)
        g = np.dot(a, b) / np.dot(b, b)              # ganho de melhor ajuste
        erro = a - g * b
        snr = 10 * np.log10(np.sum(a ** 2) / np.sum(erro ** 2))
        fc, _, pdb = corte_banda(b, sr)
        espectros[f"{r['codec']} {r['kbps_nominal']}k"] = pdb
        linhas.append({**r.to_dict(), 'kbps_calc_duracao': round(r['bytes'] * 8 / dur / 1000, 1),
                       'reducao_vs_wav_pct': round(100 * (1 - r['bytes'] / bytes_wav), 2),
                       'taxa_compressao': round(bytes_wav / r['bytes'], 1),
                       'banda_ate_kHz': round(fc / 1000, 1), 'snr_forma_onda_dB': round(snr, 1),
                       'atraso_amostras': atraso})
    # âncora: passa-baixas 3,5 kHz (como no Lab4.4)
    with tempfile.NamedTemporaryFile(suffix='.wav') as t:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(midia / 'audio' / 'referencia.wav'),
                        '-af', 'lowpass=f=3500', '-c:a', 'pcm_s16le', t.name], check=True)
        _, anc = wavfile.read(t.name)
    anc = anc.astype(np.float64).mean(axis=1) / 32768
    espectros['Âncora (LP 3,5 kHz)'] = corte_banda(anc, sr)[2]
    tab = pd.DataFrame(linhas)
    tab.to_csv(DADOS / 'metricas_audio.csv', index=False)
    print(f'Referência: {dur:.2f} s, {sr} Hz estéreo, {bytes_wav} bytes, banda até {fc_ref/1000:.1f} kHz')
    print(tab[['codec', 'kbps_nominal', 'kbps_efetivo', 'bytes', 'reducao_vs_wav_pct', 'taxa_compressao',
               'banda_ate_kHz', 'snr_forma_onda_dB']].to_string(index=False))

    # Fig. 1 — PSD média de cada versão
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, taxa in zip(axs, (48, 128)):
        ax.plot(f / 1000, espectros['Referência WAV'], color='black', lw=1.4, label='Referência WAV')
        for c in ('MP3', 'AAC', 'Vorbis'):
            ax.plot(f / 1000, espectros[f'{c} {taxa}k'], color=COR[c], lw=1, label=f'{c} {taxa} kbit/s')
        if taxa == 48:
            ax.plot(f / 1000, espectros['Âncora (LP 3,5 kHz)'], color='grey', ls='--', lw=1, label='Âncora LP 3,5 kHz')
        ax.set(title=f'Espectro médio — {taxa} kbit/s', xlabel='Frequência (kHz)', xlim=(0, 22.05), ylim=(-110, 3))
        ax.axhline(-60, color='grey', lw=0.5, ls=':')
        ax.legend(frameon=False, fontsize=7, loc='lower left')
    axs[0].set_ylabel('PSD relativa (dB)')
    fig.tight_layout(); fig.savefig(FIG / 'audio_espectro_medio.png'); plt.close(fig)

    # Fig. 2 — espectrogramas
    versoes = [('Referência WAV', None), ('MP3 48 kbit/s', 'mp3_48k.mp3'), ('AAC 48 kbit/s', 'aac_48k.m4a'),
               ('Vorbis 48 kbit/s', 'vorbis_48k.ogg'), ('MP3 128 kbit/s', 'mp3_128k.mp3'), ('Âncora LP 3,5 kHz', 'ANC')]
    fig, axs = plt.subplots(2, 3, figsize=(11, 5.2), sharex=True, sharey=True)
    for ax, (nome, arq) in zip(axs.flat, versoes):
        x = ref if arq is None else anc if arq == 'ANC' else alinhar(ref, decodificar(midia / 'audio' / 'codificados' / arq))[1]
        ff, tt, S = signal.spectrogram(x, sr, nperseg=1024, noverlap=768)
        ax.pcolormesh(tt, ff / 1000, 10 * np.log10(S + 1e-14), vmin=-120, vmax=-30, cmap='magma', shading='auto')
        ax.set_title(nome)
    for ax in axs[:, 0]: ax.set_ylabel('kHz')
    for ax in axs[1]: ax.set_xlabel('tempo (s)')
    fig.tight_layout(); fig.savefig(FIG / 'audio_espectrogramas.png'); plt.close(fig)

    # Fig. 3 — tamanho x taxa
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for c in ('MP3', 'AAC', 'Vorbis'):
        d = tab[tab.codec == c]
        ax.plot(d.kbps_efetivo, d.bytes / 1024, 'o-', color=COR[c], label=c)
    ax.axhline(bytes_wav / 1024, color='black', ls='--', lw=1)
    ax.text(50, bytes_wav / 1024 * 0.93, f'WAV PCM 16 bit: {bytes_wav/1024:.0f} KiB', fontsize=8, va='top')
    ax.set(xlabel='Bitrate efetivo (kbit/s)', ylabel='Tamanho (KiB)', title='Tamanho dos arquivos de áudio')
    ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / 'audio_tamanho.png'); plt.close(fig)
    return tab


def imagem(midia):
    med = pd.read_csv(DADOS / 'medidas_imagem.csv')
    linhas = []
    for _, r in med.iterrows():
        o = np.asarray(Image.open(midia / 'imagens' / 'originais' / r['imagem']).convert('RGB'))
        j = np.asarray(Image.open(midia / 'imagens' / 'jpeg' / r['arquivo_jpeg']).convert('RGB'))
        linhas.append({**r.to_dict(), 'psnr_dB': round(psnr(o, j, data_range=255), 2),
                       'ssim': round(ssim(o, j, channel_axis=2, data_range=255), 4),
                       'bpp': round(r['bytes_jpeg'] * 8 / (o.shape[0] * o.shape[1]), 3),
                       'taxa_compressao': round(r['bytes_original'] / r['bytes_jpeg'], 1)})
    tab = pd.DataFrame(linhas)
    tab.to_csv(DADOS / 'metricas_imagem.csv', index=False)
    resumo = tab.groupby('q_ffmpeg').agg(bytes_medio=('bytes_jpeg', 'mean'), reducao_media_pct=('reducao_pct', 'mean'),
                                         reducao_min=('reducao_pct', 'min'), reducao_max=('reducao_pct', 'max'),
                                         bpp=('bpp', 'mean'), psnr_dB=('psnr_dB', 'mean'), ssim=('ssim', 'mean'))
    resumo.round(3).to_csv(DADOS / 'resumo_metricas_imagem.csv')
    print(resumo.round(3).to_string())

    # Fig. 4 — redução e PSNR por q
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
    for nome, d in tab.groupby('imagem'):
        axs[0].plot(d.q_ffmpeg, d.reducao_pct, 'o-', color='#999', lw=0.8, ms=3)
        axs[1].plot(d.q_ffmpeg, d.psnr_dB, 'o-', color='#999', lw=0.8, ms=3)
    axs[0].plot(resumo.index, resumo.reducao_media_pct, 'o-', color='#2a6fdb', lw=2, label='média (7 imagens)')
    axs[1].plot(resumo.index, resumo.psnr_dB, 'o-', color='#2a6fdb', lw=2, label='média (7 imagens)')
    axs[0].set(xlabel='-q:v (FFmpeg)', ylabel='Redução vs PNG (%)', title='Redução de dados', xticks=[2, 20, 31])
    axs[1].set(xlabel='-q:v (FFmpeg)', ylabel='PSNR (dB)', title='Fidelidade objetiva (PSNR)', xticks=[2, 20, 31])
    for ax in axs: ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG / 'imagem_reducao_psnr.png'); plt.close(fig)

    # Fig. 5 — recortes ampliados (sem rostos): área uniforme, borda e textura da imagem coletiva
    nome = 'G4_1792112691'
    o = Image.open(midia / 'imagens' / 'originais' / f'{nome}.png').convert('RGB')
    regioes = {'Área uniforme escura\n(camiseta preta)': (5, 395, 85, 455),
               'Bordas finas\n(texto do livro)': (105, 78, 185, 138),
               'Cor saturada\n(camiseta laranja)': (100, 380, 180, 440),
               'Textura + borda\n(olho da pelúcia)': (330, 280, 410, 340)}
    versoes = [('PNG original', o)] + [(f'q:v {q}', Image.open(midia / 'imagens' / 'jpeg' / f'{nome}_q{q}.jpg').convert('RGB'))
                                         for q in (2, 20, 31)]
    fig, axs = plt.subplots(len(regioes), 4, figsize=(9, 2.25 * len(regioes)))
    for i, (rot, cx) in enumerate(regioes.items()):
        for k, (vn, im) in enumerate(versoes):
            axs[i, k].imshow(im.crop(cx).resize(((cx[2]-cx[0]) * 4, (cx[3]-cx[1]) * 4), Image.NEAREST))
            axs[i, k].set_xticks([]); axs[i, k].set_yticks([])
            if i == 0: axs[i, k].set_title(vn)
        axs[i, 0].set_ylabel(rot, fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / 'imagem_recortes.png'); plt.close(fig)

    # Fig. 6 — mapa de erro absoluto (q31) — onde o JPEG mais altera a imagem
    j31 = np.asarray(Image.open(midia / 'imagens' / 'jpeg' / f'{nome}_q31.jpg').convert('L'), dtype=float)
    o_l = np.asarray(o.convert('L'), dtype=float)
    err = np.abs(o_l - j31)
    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    im = ax.imshow(err, cmap='inferno', vmin=0, vmax=40); ax.set_axis_off()
    ax.set_title('|original − JPEG q:v 31| (luminância)')
    fig.colorbar(im, ax=ax, fraction=0.035, label='erro (níveis de 0–255)')
    fig.tight_layout(); fig.savefig(FIG / 'imagem_mapa_erro_q31.png'); plt.close(fig)

    # erro médio por tipo de região (blocos 8x8 classificados pela variância do original)
    h, w = (o_l.shape[0] // 8) * 8, (o_l.shape[1] // 8) * 8
    blocos_o = o_l[:h, :w].reshape(h // 8, 8, w // 8, 8).swapaxes(1, 2).reshape(-1, 64)
    regs = []
    for q in (2, 20, 31):
        jq = np.asarray(Image.open(midia / 'imagens' / 'jpeg' / f'{nome}_q{q}.jpg').convert('L'), dtype=float)
        blocos_j = jq[:h, :w].reshape(h // 8, 8, w // 8, 8).swapaxes(1, 2).reshape(-1, 64)
        var = blocos_o.std(axis=1)
        classe = np.select([var < 3, var < 15], ['uniforme (dp<3)', 'intermediária'], 'textura/borda (dp≥15)')
        rmse = np.sqrt(((blocos_o - blocos_j) ** 2).mean(axis=1))
        for c in np.unique(classe):
            regs.append({'q_ffmpeg': q, 'regiao': c, 'n_blocos': int((classe == c).sum()),
                         'rmse_medio': round(rmse[classe == c].mean(), 2)})
    reg = pd.DataFrame(regs).pivot(index='regiao', columns='q_ffmpeg', values='rmse_medio')
    reg.to_csv(DADOS / 'erro_por_regiao_G4_1792112691.csv')
    print('\nRMSE médio por tipo de bloco 8x8 (imagem coletiva):\n', reg.to_string())
    return tab


def notas():
    fa, fi = DADOS / 'notas_audio_completas.csv', DADOS / 'notas_imagem_completas.csv'
    if fa.is_file():
        d = pd.read_csv(fa)
        ordem = d.groupby('condicao')['nota_0_100'].mean().sort_values(ascending=False).index
        fig, ax = plt.subplots(figsize=(6, 3.2))
        ax.boxplot([d[d.condicao == c].nota_0_100 for c in ordem])
        ax.set_xticks(range(1, len(ordem) + 1), list(ordem))
        for i, c in enumerate(ordem, 1):
            ax.scatter(np.full((d.condicao == c).sum(), i), d[d.condicao == c].nota_0_100, s=12, color='#2a6fdb', zorder=3)
        ax.set(ylim=(0, 100), ylabel='Nota (0–100)', title='Notas MUSHRA-like — pacote de áudio do G4')
        plt.setp(ax.get_xticklabels(), rotation=20); fig.tight_layout(); fig.savefig(FIG / 'notas_audio.png'); plt.close(fig)
        print('Figura de notas de áudio gerada.')
    if fi.is_file():
        d = pd.read_csv(fi)
        fig, ax = plt.subplots(figsize=(4.8, 3.2))
        ax.scatter(d.reducao_pct, d.diferenca_0_3 + np.random.uniform(-.06, .06, len(d)), color='#2a6fdb')
        m = d.groupby('reducao_pct').diferenca_0_3.mean()
        ax.plot(m.index, m.values, 'k-o')
        ax.set(xlabel='Redução de dados (%)', ylabel='Diferença percebida (0–3)', ylim=(-0.3, 3.3),
               title='Diferença percebida — pacote de imagens do G4')
        fig.tight_layout(); fig.savefig(FIG / 'notas_imagem.png'); plt.close(fig)
        print('Figura de notas de imagem gerada.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--midia', type=Path, help='pasta Lab4_CSM/G4 baixada do Drive')
    a = ap.parse_args()
    if a.midia:
        audio(a.midia); imagem(a.midia)
    notas()
