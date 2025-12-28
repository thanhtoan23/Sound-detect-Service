"""
smart_audio_pipeline.py
Kết hợp AudioProcessor (lọc nhiễu) và AudioClassifier (nhận diện AI)
"""
import time
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.live import Live

from audio_classifier import AudioClassifier, SoundType
from audio_processor import AudioProcessor


class SmartAudioSystem:
    def __init__(self):
        self.processor = AudioProcessor(rate=16000)
        self.classifier = AudioClassifier(rate=16000)
        self.is_running = False
        self.console = Console()

    def start(self):
        self.classifier.start_stream()
        self.is_running = True
        if hasattr(self.processor, "reset_states"):
            self.processor.reset_states()
        self.console.print("[bold green]Smart Audio Pipeline Started...[/bold green]")

    def stop(self):
        self.is_running = False
        self.classifier.stop_stream()
        self.console.print("[bold red]Stopped.[/bold red]")

    def process_and_predict(self):
        # 1) Raw
        raw_chunk = self.classifier.read_audio_chunk()
        if raw_chunk is None:
            return None

        # 2) DSP
        clean_chunk = self.processor.process(raw_chunk)

        # 3) Classify (đã có smoothing + threshold->unknown trong audio_classifier.py)
        basic_type, features = self.classifier.classify_chunk(clean_chunk)

        env_label = features.get("env_label")
        env_conf = float(features.get("env_conf", 0.0))

        return {
            "basic_type": basic_type,
            "env_label": env_label,
            "env_conf": env_conf,
            "rms_raw": float(np.sqrt(np.mean(raw_chunk**2) + 1e-9)),
            "rms_clean": float(features.get("rms", 0.0)),
            "gain_applied": getattr(self.processor, "current_gain", 1.0)
        }

    def run_demo(self):
        self.start()

        try:
            table = Table(title="Smart Audio Analysis (DSP + AI)", show_lines=True)
            table.add_column("DSP Status", style="cyan", width=25)
            table.add_column("Basic Type", style="magenta", width=15)
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
                        basic = result["basic_type"].value.upper()

                        if result["env_label"] is None:
                            ai_text = "N/A (buffer/hop/rms)"
                        else:
                            conf_percent = result["env_conf"] * 100
                            color = "bold green" if conf_percent > 70 else "yellow"
                            ai_text = f"[{color}]{result['env_label'].upper()}\n({conf_percent:.1f}%)[/{color}]"

                        # refresh table
                        table = Table(title="Smart Audio Analysis (DSP + AI)", box=None)
                        table.add_column("DSP Processing", style="dim cyan")
                        table.add_column("Basic Detection", style="magenta")
                        table.add_column("AI Classification", style="bold white")
                        table.add_row(dsp_info, basic, ai_text)
                        live.update(table)

                    time.sleep(0.05)

        except KeyboardInterrupt:
            self.stop()


if __name__ == "__main__":
    system = SmartAudioSystem()
    system.run_demo()
