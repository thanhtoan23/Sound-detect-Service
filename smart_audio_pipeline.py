"""
smart_audio_pipeline.py
Kết hợp AudioProcessor (lọc nhiễu) và AudioClassifier (AI-only)
"""
import time
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.live import Live

from audio_classifier import AudioClassifier
from audio_processor import AudioProcessor


class SmartAudioSystem:
    def __init__(self):
        self.processor = AudioProcessor(rate=16000)
        self.classifier = AudioClassifier(rate=16000)
        self.is_running = False
        self.console = Console()

    def start(self):
        self.classifier.start()
        self.is_running = True
        if hasattr(self.processor, "reset_states"):
            self.processor.reset_states()
        self.console.print("[bold green]Smart Audio Pipeline Started...[/bold green]")

    def stop(self):
        self.is_running = False
        self.classifier.stop()
        self.console.print("[bold red]Stopped.[/bold red]")

    def process_and_predict(self):
        # 1) Raw
        raw_chunk = self.classifier.read_audio_chunk()
        if raw_chunk is None:
            return None

        # 2) DSP
        clean_chunk = self.processor.process(raw_chunk)

        # 3) AI-only classify: returns (label, conf, rms)
        env_label, env_conf, rms_clean = self.classifier.classify_chunk(clean_chunk)

        return {
            "env_label": env_label,
            "env_conf": float(env_conf),
            "rms_raw": float(np.sqrt(np.mean(raw_chunk**2) + 1e-9)),
            "rms_clean": float(rms_clean),
            "gain_applied": float(getattr(self.processor, "current_gain", 1.0)),
        }

    def run_demo(self):
        self.start()

        try:
            table = Table(title="Smart Audio Analysis (DSP + AI)", show_lines=True)
            table.add_column("DSP Status", style="cyan", width=25)
            table.add_column("AI Prediction (Smoothed)", style="green", justify="center")

            with Live(table, refresh_per_second=4, console=self.console) as live:
                while self.is_running:
                    result = self.process_and_predict()

                    if result:
                        dsp_info = (
                            f"Gain: {result['gain_applied']:.1f}x\n"
                            f"RMS In : {result['rms_raw']:.4f}\n"
                            f"RMS Out: {result['rms_clean']:.4f}"
                        )

                        if result["env_label"] is None:
                            ai_text = "N/A (buffer/hop/rms)"
                        else:
                            conf_percent = result["env_conf"] * 100
                            color = "bold green" if conf_percent > 70 else "yellow"
                            ai_text = f"[{color}]{str(result['env_label']).upper()}\n({conf_percent:.1f}%)[/{color}]"

                        table = Table(title="Smart Audio Analysis (DSP + AI)", box=None)
                        table.add_column("DSP Processing", style="dim cyan")
                        table.add_column("AI Classification", style="bold white")
                        table.add_row(dsp_info, ai_text)
                        live.update(table)

                    time.sleep(0.05)

        except KeyboardInterrupt:
            self.stop()


if __name__ == "__main__":
    system = SmartAudioSystem()
    system.run_demo()
