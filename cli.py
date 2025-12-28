"""Modern CLI for ReSpeaker Sound Detection Service"""

import sys
import argparse
import time
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from sound_detector import SoundDetector
from audio_classifier import AudioClassifier
from smart_audio_pipeline import SmartAudioSystem
import config

console = Console()


def print_header(text, style="bold cyan"):
    console.print(Panel(f"[{style}]{text}[/{style}]", box=box.DOUBLE))


def print_error(text):
    console.print(f"[bold red]ERROR:[/bold red] {text}")


def print_success(text):
    console.print(f"[bold green]SUCCESS:[/bold green] {text}")


def print_info(text):
    console.print(f"[blue]INFO:[/blue] {text}")


def cmd_start(args):
    print_header("Starting Smart Audio Monitor")
    
    try:
        system = SmartAudioSystem()
        detector = SoundDetector()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Initializing...", total=None)
            if not detector.connect():
                print_error("Cannot connect to ReSpeaker device")
                return
            system.start()
            progress.update(task, description="[green]System started!")
        
        print_success("System is running")
        
        if args.monitor:
            console.print("\n[yellow]Monitor Mode[/yellow] (Press Ctrl+C to stop)\n")
            monitor_live(system, detector)
            system.stop()
            detector.disconnect()
            print_success("System stopped")
        else:
            print_info("System running. Use Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                system.stop()
                detector.disconnect()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping service...[/yellow]")
        if 'service' in locals():
            try:
                service.stop()
            except:
                pass
        print_success("Service stopped")
    except Exception as e:
        print_error(f"Failed to start service: {e}")
        if 'service' in locals():
            try:
                service.stop()
            except:
                pass
        sys.exit(1)


def monitor_live(system, detector):
    """Monitor AI classification in real-time"""
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold]RMS In | RMS Out | Gain | Direction | AI Label (Confidence)[/bold]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    
    detections = {}
    
    try:
        while True:
            result = system.process_and_predict()
            direction = detector.get_direction()
            
            if result:
                rms_in = result['rms_raw']
                rms_out = result['rms_clean']
                gain = result['gain_applied']
                label = result.get('env_label', 'unknown')
                conf = result.get('env_conf', 0.0) * 100
                
                dir_str = f"{direction:>3}°" if direction else " N/A"
                
                # Track detections
                if label and label != 'unknown':
                    detections[label] = detections.get(label, 0) + 1
                
                # Color based on confidence
                if conf > 70:
                    color = 'green'
                elif conf > 50:
                    color = 'yellow'
                else:
                    color = 'dim'
                
                console.print(
                    f"{rms_in:6.3f} | {rms_out:7.3f} | {gain:4.1f}x | {dir_str:9} | "
                    f"[{color}]{label:12} ({conf:5.1f}%)[/{color}]"
                )
            
            time.sleep(0.15)
            
    except KeyboardInterrupt:
        console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]DETECTION SUMMARY[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
        
        if detections:
            table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("AI Label", style="cyan", width=20)
            table.add_column("Count", style="green", width=10, justify="right")
            table.add_column("Bar", style="blue", width=30)
            
            total = sum(detections.values())
            for label, count in sorted(detections.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                bar = "█" * int(percentage / 3)
                
                table.add_row(
                    f"[green]{label.upper()}[/green]",
                    str(count),
                    f"[blue]{bar}[/blue] {percentage:.1f}%"
                )
            
            console.print(table)
            console.print(f"\n[bold]Total detections: {total}[/bold]")
        else:
            console.print("[dim]No detections recorded[/dim]")
        
        console.print("\n[yellow]Monitor stopped[/yellow]")


def cmd_status(args):
    """Show device status"""
    print_header("Device Status")
    
    try:
        detector = SoundDetector()
        detector.connect()
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Connection", "Connected" if detector.connected else "Not Connected")
        
        if detector.connected:
            table.add_row("VAD", "Active" if detector.is_voice_detected() else "Inactive")
            table.add_row("Direction", f"{detector.get_direction()}°")
            table.add_row("Device", "ReSpeaker Mic Array v2.0")
        
        console.print(table)
        detector.disconnect()
        
    except Exception as e:
        print_error(f"Failed to get status: {e}")
        sys.exit(1)


def cmd_test_vad(args):
    """Test VAD and DOA"""
    print_header("Testing VAD & DOA")
    
    try:
        detector = SoundDetector()
        detector.connect()
        
        print_info(f"Monitoring for {args.duration} seconds...")
        print_info("Speak or make sounds to test!\n")
        
        console.print("[dim]Time     │ VAD    │ Speech │ Direction[/dim]")
        console.print("[dim]─────────┼────────┼────────┼──────────[/dim]")
        
        start_time = time.time()
        detections = []
        
        while time.time() - start_time < args.duration:
            status = detector.get_status()
            timestamp = time.strftime("%H:%M:%S")
            
            vad = "YES" if status['vad'] else "NO"
            speech = "YES" if status['speech'] else "NO"
            direction = f"{status['direction']}°" if status['direction'] else "N/A"
            
            vad_color = "red" if status['vad'] else "dim"
            console.print(f"[dim]{timestamp}[/dim] │ [{vad_color}]{vad:^6}[/{vad_color}] │ {speech:^6} │ [green]{direction:>8}[/green]")
            
            detections.append(status)
            time.sleep(0.5)
        
        console.print("\n" + "─" * 50)
        vad_count = sum(1 for d in detections if d['vad'])
        speech_count = sum(1 for d in detections if d['speech'])
        
        table = Table(show_header=False, box=box.SIMPLE, show_edge=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total samples", str(len(detections)))
        table.add_row("VAD detections", f"{vad_count} ({vad_count/len(detections)*100:.1f}%)")
        table.add_row("Speech detections", f"{speech_count} ({speech_count/len(detections)*100:.1f}%)")
        
        console.print(table)
        detector.disconnect()
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        sys.exit(1)


def cmd_test_audio(args):
    """Test audio classification"""
    print_header("Testing AI Audio Classification")
    
    try:
        classifier = AudioClassifier()
        detector = SoundDetector()
        
        print_info(f"Recording for {args.duration} seconds...")
        print_info("Make various sounds to test AI classification\n")
        
        detector_available = detector.connect()
        
        try:
            classifier.start()
        except Exception as e:
            print_error(f"Failed to start audio stream: {e}")
            return
        
        if detector_available:
            console.print("[dim]AI Label      │ Confidence │ RMS    │ Direction[/dim]")
            console.print("[dim]──────────────┼────────────┼────────┼──────────[/dim]")
        else:
            console.print("[dim]AI Label      │ Confidence │ RMS[/dim]")
            console.print("[dim]──────────────┼────────────┼────────[/dim]")
        
        label_counts = {}
        start_time = time.time()
        
        while time.time() - start_time < args.duration:
            label, conf, rms = classifier.classify_audio()
            
            if label:
                label_counts[label] = label_counts.get(label, 0) + 1
            
            direction = None
            if detector_available:
                direction = detector.get_direction()
            
            # Color based on confidence
            if conf > 0.7:
                color = 'green'
            elif conf > 0.5:
                color = 'yellow'
            else:
                color = 'dim'
            
            label_str = label if label else 'unknown'
            
            if detector_available and direction is not None:
                console.print(f"[{color}]{label_str:14}[/{color}] │ {conf*100:9.1f}% │ {rms:6.3f} │ [{color}]{direction:>3}°[/{color}]")
            else:
                console.print(f"[{color}]{label_str:14}[/{color}] │ {conf*100:9.1f}% │ {rms:6.3f}")
            
            time.sleep(0.3)
        
        if detector_available:
            detector.disconnect()
        
        console.print("\n" + "═" * 60)
        console.print("[bold cyan]SUMMARY[/bold cyan]")
        console.print("═" * 60 + "\n")
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("AI Label", style="cyan", width=15)
        table.add_column("Count", style="green", width=10)
        table.add_column("Percentage", style="yellow", width=15)
        table.add_column("Bar", style="blue", width=30)
        
        total = sum(label_counts.values())
        for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            bar = "█" * int(percentage / 3.33)
            
            table.add_row(
                f"[green]{label.upper()}[/green]",
                str(count),
                f"{percentage:.1f}%",
                f"[blue]{bar}[/blue]"
            )
        
        console.print(table)
        classifier.stop()
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="ReSpeaker Smart Audio Monitor - AI Classification CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --monitor          Start and monitor AI classification
  %(prog)s status                   Check ReSpeaker device status  
  %(prog)s test-vad --duration 10   Test VAD/DOA for 10 seconds
  %(prog)s test-audio               Test AI audio classification
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    start_parser = subparsers.add_parser('start', help='Start the system')
    start_parser.add_argument('--monitor', action='store_true', help='Monitor mode')
    
    subparsers.add_parser('status', help='Show device status')
    
    test_vad_parser = subparsers.add_parser('test-vad', help='Test VAD & DOA')
    test_vad_parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    
    test_audio_parser = subparsers.add_parser('test-audio', help='Test AI audio classification')
    test_audio_parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        'start': cmd_start,
        'status': cmd_status,
        'test-vad': cmd_test_vad,
        'test-audio': cmd_test_audio
    }
    
    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == '__main__':
    main()
