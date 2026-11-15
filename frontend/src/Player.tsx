import { useEffect, useRef, useState } from "react";
import { SPEEDS, formatClock, playbackRatio, simulatedTimeAt, speedLabel } from "./lib";

const LOOP_KEY = "flamelab.player.loop";

function readLoop(): boolean {
  try { return localStorage.getItem(LOOP_KEY) !== "0"; } catch { return true; }
}

/** Player persistente do vídeo gerado pelo Smokeview: pausa, repetição, velocidade, linha do tempo, tela cheia. */
export default function VideoPlayer({ src, poster, simulatedTotal }: { src: string; poster?: string; simulatedTotal?: number | null }) {
  const box = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState<number>(1);
  const [loop, setLoop] = useState<boolean>(readLoop);
  const [error, setError] = useState(false);
  const [ended, setEnded] = useState(false);

  useEffect(() => { if (video.current) video.current.playbackRate = speed; }, [speed]);
  useEffect(() => { if (video.current) video.current.loop = loop; try { localStorage.setItem(LOOP_KEY, loop ? "1" : "0"); } catch { /* sem armazenamento */ } }, [loop]);

  const toggle = () => { const v = video.current; if (!v) return; if (v.paused) { void v.play(); } else v.pause(); };
  const replay = () => { const v = video.current; if (!v) return; v.currentTime = 0; setEnded(false); void v.play(); };
  const fullscreen = () => { const el = box.current; if (!el) return; if (document.fullscreenElement) void document.exitFullscreen(); else void el.requestFullscreen?.(); };
  const sim = simulatedTimeAt(time, duration, simulatedTotal);
  const ratio = playbackRatio(duration, simulatedTotal);

  if (error) return <div className="box bad" role="alert">O vídeo não pôde ser carregado. O arquivo existe na lista de artefatos, mas o navegador não conseguiu reproduzi-lo.</div>;
  return (
    <div className="player" ref={box} onKeyDown={(e) => { if (e.key === " " && e.target === e.currentTarget) { e.preventDefault(); toggle(); } }} tabIndex={0} aria-label="Player do vídeo da simulação">
      <video ref={video} src={src} poster={poster} preload="auto" playsInline onClick={toggle}
        onPlay={() => { setPlaying(true); setEnded(false); }} onPause={() => setPlaying(false)} onEnded={() => { setPlaying(false); setEnded(true); }}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)} onLoadedMetadata={(e) => { setDuration(e.currentTarget.duration); e.currentTarget.playbackRate = speed; e.currentTarget.loop = loop; }}
        onError={() => setError(true)} />
      <div className="controls">
        <button onClick={toggle} aria-label={playing ? "Pausar" : "Reproduzir"}>{playing ? "⏸ Pausar" : "▶ Reproduzir"}</button>
        <button onClick={replay} aria-label="Reproduzir novamente">↺ Reproduzir novamente</button>
        <input type="range" min={0} max={duration || 0} step={0.01} value={Math.min(time, duration || 0)} aria-label="Linha do tempo"
          onChange={(e) => { if (video.current) video.current.currentTime = Number(e.target.value); }} className="timeline" />
        <span className="clock" aria-live="off">{formatClock(time)} / {formatClock(duration)}</span>
      </div>
      <div className="controls">
        <span className="muted">Velocidade:</span>
        {SPEEDS.map((s) => <button key={s} className={s === speed ? "on" : ""} aria-pressed={s === speed} onClick={() => setSpeed(s)}>{speedLabel(s)}</button>)}
        <label className="row"><input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} /> Repetir automaticamente</label>
        <button onClick={fullscreen}>⛶ Tela cheia</button>
      </div>
      <div className="detail">
        Duração do vídeo: <strong>{formatClock(duration)}</strong>
        {sim != null && <> · tempo físico simulado neste instante ≈ <strong>{sim.toFixed(1).replace(".", ",")} s</strong> de {simulatedTotal} s</>}
        {ratio != null && <> · {ratio > 1.05 ? `reprodução ${ratio.toFixed(1).replace(".", ",")}× mais rápida que o tempo físico (use 0,25× para ver devagar)` : ratio < 0.95 ? `reprodução ${(1 / ratio).toFixed(1).replace(".", ",")}× mais lenta que o tempo físico` : "1 s de vídeo = 1 s de tempo físico simulado"}</>}
        {ended && !loop && <> · fim do vídeo — use “Reproduzir novamente”.</>}
      </div>
    </div>
  );
}
