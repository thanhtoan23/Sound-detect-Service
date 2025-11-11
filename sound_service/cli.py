"""
Modern CLI for ReSpeaker Sound Detection Service
Beautiful command-line interface with rich library
"""

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
from led_visualizer import LEDVisualizer
from sound_service import SoundDetectionService
import config

console = Console()


def print_header(text, style="bold cyan"):
    """Print beautiful header"""
    console.print(Panel(f"[{style}]{text}[/{style}]", box=box.DOUBLE))


def print_error(text):
    """Print error message"""
    console.print(f"[bold red]✗[/bold red] {text}")


def print_success(text):
    """Print success message"""
    console.print(f"[bold green]✓[/bold green] {text}")


def print_info(text):
    """Print info message"""
    console.print(f"[blue]ℹ[/blue] {text}")


def cmd_start(args):
    """Start the sound detection service"""
    print_header("🚀 Starting Sound Detection Service")
    
    try:
        service = SoundDetectionService(
            use_led=not args.no_led,
            use_classifier=not args.no_classifier
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
        else:
            print_info("Service running in background. Use 'monitor' command to view status.")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping service...[/yellow]")
        if 'service' in locals():
            service.stop()
        print_success("Service stopped")
    except Exception as e:
        print_error(f"Failed to start service: {e}")
        sys.exit(1)


def monitor_service_live(service):
    """Live monitor with beautiful UI"""
    
    def create_status_table():
        """Create status display table"""
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("🎤 VAD", style="cyan", width=10)
        table.add_column("🗣️ Speech", style="yellow", width=10)
        table.add_column("🧭 Direction", style="green", width=12)
        table.add_column("🎵 Sound Type", style="blue", width=15)
        table.add_column("📊 Count", style="magenta", width=10)
        
        status = service.get_current_status()
        stats = service.get_statistics()
        
        vad = "🔴 Yes" if status.get('vad') else "⚪ No"
        speech = "✓" if status.get('speech') else "✗"
        direction = f"{status.get('direction', 'N/A')}°"
        sound_type = status.get('sound_type', 'unknown').upper()
        count = stats.get('total_detections', 0)
        
        # Color coding
        sound_color = {
            'SPEECH': 'green',
            'MUSIC': 'blue', 
            'NOISE': 'red',
            'SILENCE': 'dim',
            'UNKNOWN': 'white'
        }.get(sound_type, 'white')
        
        table.add_row(
            vad,
            speech,
            direction,
            f"[{sound_color}]{sound_type}[/{sound_color}]",
            str(count)
        )
        
        return table
    
    def create_stats_panel():
        """Create statistics panel"""
        stats = service.get_statistics()
        
        text = Text()
        text.append("📈 Statistics\n\n", style="bold cyan")
        
        for sound_type, count in stats.get('by_type', {}).items():
            percentage = stats.get('percentages', {}).get(sound_type, 0)
            bar = "█" * int(percentage / 5)
            text.append(f"{sound_type:8} ", style="white")
            text.append(f"{bar:20} ", style="green")
            text.append(f"{count:3} ({percentage:.1f}%)\n", style="dim")
        
        return Panel(text, box=box.ROUNDED, border_style="cyan")
    
    try:
        with Live(create_status_table(), refresh_per_second=2, console=console) as live:
            while True:
                layout = Layout()
                layout.split_column(
                    Layout(create_status_table(), size=6),
                    Layout(create_stats_panel())
                )
                live.update(layout)
                time.sleep(config.MONITOR_REFRESH_RATE)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")


def cmd_status(args):
    """Show device status"""
    print_header("📊 Device Status")
    
    try:
        detector = SoundDetector()
        detector.connect()
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("🔌 Connection", "✓ Connected" if detector.connected else "✗ Not Connected")
        
        if detector.connected:
            table.add_row("🎤 VAD", "Active" if detector.is_voice_detected() else "Inactive")
            table.add_row("🧭 Direction", f"{detector.get_direction()}°")
            table.add_row("📡 Device", "ReSpeaker Mic Array v2.0")
        
        console.print(table)
        detector.disconnect()
        
    except Exception as e:
        print_error(f"Failed to get status: {e}")
        sys.exit(1)


def cmd_test_vad(args):
    """Test VAD and DOA"""
    print_header("🎤 Testing VAD & DOA")
    
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
            
            vad = "🔴" if status['vad'] else "⚪"
            speech = "✓" if status['speech'] else "✗"
            direction = f"{status['direction']}°" if status['direction'] else "N/A"
            
            # Print line by line - real-time update
            vad_color = "red" if status['vad'] else "dim"
            console.print(f"[dim]{timestamp}[/dim] │ [{vad_color}]{vad:^6}[/{vad_color}] │ {speech:^6} │ [green]{direction:>8}[/green]")
            
            detections.append(status)
            time.sleep(0.5)
        
        # Summary at the end
        console.print("\n" + "─" * 50)
        vad_count = sum(1 for d in detections if d['vad'])
        speech_count = sum(1 for d in detections if d['speech'])
        
        table = Table(show_header=False, box=box.SIMPLE, show_edge=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("📊 Total samples", str(len(detections)))
        table.add_row("🔴 VAD detections", f"{vad_count} ({vad_count/len(detections)*100:.1f}%)")
        table.add_row("🗣️ Speech detections", f"{speech_count} ({speech_count/len(detections)*100:.1f}%)")
        
        console.print(table)
        detector.disconnect()
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        sys.exit(1)


def cmd_test_audio(args):
    """Test audio classification"""
    print_header("🎵 Testing Audio Classification")
    
    try:
        # Initialize both classifier and detector
        classifier = AudioClassifier()
        detector = SoundDetector()
        
        print_info(f"Recording for {args.duration} seconds...")
        print_info("Try: speaking, playing music, making noise, or staying silent\n")
        
        # Connect detector for direction
        detector_available = detector.connect()
        
        if not classifier.start_stream():
            print_error("Failed to start audio stream")
            return
        
        # Print header
        if detector_available:
            console.print("[dim]Type       │ RMS    │ ZCR      │ Direction[/dim]")
            console.print("[dim]───────────┼────────┼──────────┼──────────[/dim]")
        else:
            console.print("[dim]Type       │ RMS    │ ZCR[/dim]")
            console.print("[dim]───────────┼────────┼──────────[/dim]")
        
        # Real-time display
        sound_counts = {}
        start_time = time.time()
        sample_count = 0
        
        while time.time() - start_time < args.duration:
            sound_type, features = classifier.classify_audio()
            sound_counts[sound_type.value] = sound_counts.get(sound_type.value, 0) + 1
            sample_count += 1
            
            # Get direction if available
            direction = None
            if detector_available:
                direction = detector.get_direction()
            
            # Color for each type
            color_map = {
                'silence': 'dim',
                'speech': 'green',
                'music': 'blue',
                'noise': 'red',
                'unknown': 'yellow'
            }
            color = color_map.get(sound_type.value, 'white')
            
            # Print current detection
            if detector_available and direction is not None:
                console.print(f"[{color}]{sound_type.value.upper():10}[/{color}] │ {features.get('rms', 0):6.0f} │ {features.get('zcr', 0):.6f} │ [green]{direction:>3}°[/green]")
            else:
                console.print(f"[{color}]{sound_type.value.upper():10}[/{color}] │ {features.get('rms', 0):6.0f} │ {features.get('zcr', 0):.6f}")
            
            time.sleep(0.5)
        
        # Cleanup detector
        if detector_available:
            detector.disconnect()
        
        # Summary at the end
        console.print("\n" + "═" * 60)
        console.print("[bold cyan]📊 SUMMARY[/bold cyan]")
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


def cmd_test_led(args):
    """Test LED visualization"""
    print_header("💡 Testing LED Visualization")
    
    try:
        led = LEDVisualizer(simulation=args.simulation)
        
        console.print("[yellow]Testing LED patterns...[/yellow]\n")
        
        # Test sound types
        for sound_type in [SoundType.SPEECH, SoundType.MUSIC, SoundType.NOISE]:
            console.print(f"  Testing {sound_type.name}...")
            led.show_sound_type(sound_type)
            time.sleep(1)
        
        # Test directions
        console.print("\n[yellow]Testing directions...[/yellow]\n")
        for angle in [0, 90, 180, 270]:
            console.print(f"  Direction {angle}°")
            led.show_direction(angle)
            time.sleep(1)
        
        led.turn_off()
        print_success("LED test complete")
        
    except Exception as e:
        print_error(f"Test failed: {e}")


def cmd_record(args):
    """Record audio to file"""
    print_header(f"🎙️ Recording to {args.output}")
    
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
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the service')
    start_parser.add_argument('--monitor', action='store_true', help='Monitor mode')
    start_parser.add_argument('--no-led', action='store_true', help='Disable LED')
    start_parser.add_argument('--no-classifier', action='store_true', help='Disable audio classification')
    
    # Status command
    subparsers.add_parser('status', help='Show device status')
    
    # Test VAD command
    test_vad_parser = subparsers.add_parser('test-vad', help='Test VAD & DOA')
    test_vad_parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    
    # Test audio command
    test_audio_parser = subparsers.add_parser('test-audio', help='Test audio classification')
    test_audio_parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    
    # Test LED command
    test_led_parser = subparsers.add_parser('test-led', help='Test LED visualization')
    test_led_parser.add_argument('--simulation', action='store_true', help='Simulation mode')
    
    # Record command
    record_parser = subparsers.add_parser('record', help='Record audio to file')
    record_parser.add_argument('output', help='Output WAV file')
    record_parser.add_argument('--duration', type=int, default=5, help='Duration in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    commands = {
        'start': cmd_start,
        'status': cmd_status,
        'test-vad': cmd_test_vad,
        'test-audio': cmd_test_audio,
        'test-led': cmd_test_led,
        'record': cmd_record
    }
    
    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == '__main__':
    main()
