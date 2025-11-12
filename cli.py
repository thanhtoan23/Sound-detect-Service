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
from audio_classifier import AudioClassifier, SoundType
from sound_service import SoundDetectionService
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
    print_header("Starting Sound Detection Service")
    
    try:
        service = SoundDetectionService(
            enable_audio_classification=not args.no_classifier
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Initializing...", total=None)
            service.start()
            progress.update(task, description="[green]Service started!")
        
        print_success("Service is running")
        
        if args.monitor:
            console.print("\n[yellow]Monitor Mode[/yellow] (Press Ctrl+C to stop)\n")
            monitor_service_live(service)
            service.stop()
            print_success("Service stopped")
        else:
            print_info("Service running in background. Use 'monitor' command to view status.")
            
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


def monitor_service_live(service):
    """Simple monitor - print each line continuously"""
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold]VAD | Volume (RMS) | Direction | Sound Type[/bold]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    
    try:
        while True:
            status = service.get_current_state()
            
            vad = "Yes" if status.get('vad') else "No "
            
            rms = status.get('rms', 0)
            
            dir_val = status.get('direction')
            direction = f"{dir_val:>3}°" if dir_val is not None else " N/A"
            
            sound_type = status.get('sound_type', 'unknown').upper()
            
            color = {
                'SPEECH': 'green',
                'MUSIC': 'blue',
                'NOISE': 'red',
                'SILENCE': 'dim',
                'UNKNOWN': 'yellow'
            }.get(sound_type, 'white')
            
            console.print(f"{vad:3} | {rms:13.0f} | {direction:9} | [{color}]{sound_type:12}[/{color}]")
            
            time.sleep(config.MONITOR_REFRESH_RATE)
            
    except KeyboardInterrupt:
        console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]STATISTICS[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
        
        stats = service.get_statistics()
        total = stats.get('total_detections', 0)
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Sound Type", style="cyan", width=15)
        table.add_column("Count", style="green", width=10, justify="right")
        table.add_column("Percentage", style="yellow", width=12, justify="right")
        table.add_column("Bar", style="blue", width=30)
        
        for sound_type, count in stats.get('by_type', {}).items():
            percentage = stats.get('percentages', {}).get(sound_type, 0)
            bar = "█" * int(percentage / 3)
            
            color = {
                'speech': 'green',
                'music': 'blue',
                'noise': 'red',
                'silence': 'white',
                'unknown': 'yellow'
            }.get(sound_type, 'white')
            
            table.add_row(
                f"[{color}]{sound_type.upper()}[/{color}]",
                str(count),
                f"{percentage:.1f}%",
                f"[{color}]{bar}[/{color}]"
            )
        
        console.print(table)
        console.print(f"\n[bold]Total detections: {total}[/bold]")
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
    print_header("Testing Audio Classification")
    
    try:
        classifier = AudioClassifier()
        detector = SoundDetector()
        
        print_info(f"Recording for {args.duration} seconds...")
        print_info("Try: speaking, playing music, making noise, or staying silent\n")
        
        detector_available = detector.connect()
        
        if not classifier.start_stream():
            print_error("Failed to start audio stream")
            return
        
        if detector_available:
            console.print("[dim]Type       │ RMS    │ ZCR      │ Direction[/dim]")
            console.print("[dim]───────────┼────────┼──────────┼──────────[/dim]")
        else:
            console.print("[dim]Type       │ RMS    │ ZCR[/dim]")
            console.print("[dim]───────────┼────────┼──────────[/dim]")
        
        sound_counts = {}
        start_time = time.time()
        
        while time.time() - start_time < args.duration:
            sound_type, features = classifier.classify_audio()
            sound_counts[sound_type.value] = sound_counts.get(sound_type.value, 0) + 1
            
            direction = None
            if detector_available:
                direction = detector.get_direction()
            
            color_map = {
                'silence': 'dim',
                'speech': 'green',
                'music': 'blue',
                'noise': 'red',
                'unknown': 'yellow'
            }
            color = color_map.get(sound_type.value, 'white')
            
            if detector_available and direction is not None:
                console.print(f"[{color}]{sound_type.value.upper():10}[/{color}] │ {features.get('rms', 0):6.0f} │ {features.get('zcr', 0):.6f} │ [green]{direction:>3}°[/green]")
            else:
                console.print(f"[{color}]{sound_type.value.upper():10}[/{color}] │ {features.get('rms', 0):6.0f} │ {features.get('zcr', 0):.6f}")
            
            time.sleep(0.5)
        
        if detector_available:
            detector.disconnect()
        
        console.print("\n" + "═" * 60)
        console.print("[bold cyan]SUMMARY[/bold cyan]")
        console.print("═" * 60 + "\n")
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Count", style="green", width=10)
        table.add_column("Percentage", style="yellow", width=15)
        table.add_column("Bar", style="blue", width=30)
        
        total = sum(sound_counts.values())
        for sound_type, count in sorted(sound_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            bar = "█" * int(percentage / 3.33)
            
            color = {
                'speech': 'green',
                'music': 'blue',
                'noise': 'red',
                'silence': 'white'
            }.get(sound_type, 'white')
            
            table.add_row(
                f"[{color}]{sound_type.upper()}[/{color}]",
                str(count),
                f"{percentage:.1f}%",
                f"[{color}]{bar}[/{color}]"
            )
        
        console.print(table)
        classifier.stop()
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        sys.exit(1)


def cmd_record(args):
    """Record audio to file"""
    print_header(f"Recording to {args.output}")
    
    try:
        classifier = AudioClassifier()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]Recording...", total=args.duration)
            classifier.record_to_file(args.output, args.duration)
            progress.update(task, completed=args.duration)
        
        print_success(f"Recorded {args.duration}s to {args.output}")
        
    except Exception as e:
        print_error(f"Recording failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="ReSpeaker Sound Detection Service - Modern CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --monitor          Start and monitor service
  %(prog)s status                   Check device status  
  %(prog)s test-vad --duration 10   Test VAD for 10 seconds
  %(prog)s test-audio               Test audio classification
  %(prog)s record output.wav        Record audio to file
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    start_parser = subparsers.add_parser('start', help='Start the service')
    start_parser.add_argument('--monitor', action='store_true', help='Monitor mode')
    start_parser.add_argument('--no-classifier', action='store_true', help='Disable audio classification')
    
    subparsers.add_parser('status', help='Show device status')
    
    test_vad_parser = subparsers.add_parser('test-vad', help='Test VAD & DOA')
    test_vad_parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    
    test_audio_parser = subparsers.add_parser('test-audio', help='Test audio classification')
    test_audio_parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    
    record_parser = subparsers.add_parser('record', help='Record audio to file')
    record_parser.add_argument('output', help='Output WAV file')
    record_parser.add_argument('--duration', type=int, default=5, help='Duration in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        'start': cmd_start,
        'status': cmd_status,
        'test-vad': cmd_test_vad,
        'test-audio': cmd_test_audio,
        'record': cmd_record
    }
    
    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == '__main__':
    main()
