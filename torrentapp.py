import libtorrent as lt
import time
import os
import sys
import questionary
import warnings
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from rich.console import Group
from rich.columns import Columns
from rich.text import Text

console = Console()
warnings.filterwarnings("ignore", category=DeprecationWarning)

def get_resume_file_name(info_hash):
    return f"{info_hash}.fastresume"

def save_resume_data(handle):
    try:
        if handle.is_valid() and handle.has_metadata():
            resume_data = lt.bencode(handle.save_resume_data())
            with open(get_resume_file_name(str(handle.info_hash())), "wb") as f:
                f.write(resume_data)
    except Exception as e:
        console.print(f"[red]⚠️ Failed to save resume data: {e}[/red]")

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def load_resume_data(info_hash):
    try:
        with open(get_resume_file_name(info_hash), "rb") as f:
            data = f.read()
            return lt.bdecode(data)
    except FileNotFoundError:
        return None
    except Exception as e:
        console.print(f"[red]⚠️ Failed to load resume data: {e}[/red]")
        return None

def main():
    console.print("[bold cyan]🔗📄 Torrent & Magnet Downloader 📄🔗[/bold cyan]\n")

    choice = questionary.select(
        "Choose the source:",
        choices=[
            "Torrent file",
            "Magnet link"
        ]
    ).ask()

    if not choice:
        console.print("[red]❌ No choice selected. Exiting.[/red]")
        sys.exit(1)

    session = lt.session()
    settings = session.get_settings()
    settings["listen_interfaces"] = "0.0.0.0:6881-6891"
    settings["enable_outgoing_utp"] = True
    settings["enable_incoming_utp"] = True
    settings["enable_outgoing_tcp"] = True
    settings["enable_incoming_tcp"] = True
    settings["max_peerlist_size"] = 5000
    settings["max_paused_peerlist_size"] = 1000
    settings["connections_limit"] = 500
    settings["download_rate_limit"] = 0
    settings["upload_rate_limit"] = 0
    settings["alert_mask"] = lt.alert.category_t.all_categories
    settings["announce_to_all_trackers"] = True
    settings["announce_to_all_tiers"] = True
    settings["peer_connect_timeout"] = 15
    settings["request_queue_time"] = 30
    settings["peer_timeout"] = 60
    settings["max_queued_disk_bytes"] = 1024 * 1024 * 32
    settings["max_rejects"] = 50

    session.add_dht_router("router.bittorrent.com", 6881)
    session.add_dht_router("dht.bittorrent.com", 6881)
    session.add_dht_router("dht.bittorrent.org", 6881)
    session.add_dht_router("router.bitcoin.com", 6881)
    session.add_dht_router("router.dht.org", 6881)
    session.add_dht_router("dht.transmissionbt.com", 6881)
    session.add_dht_router("router.utorrent.com", 6881)
    session.add_dht_router("router.bitcomet.com", 6881)
    session.add_dht_router("dht.libtorrent.org", 25401)
    session.add_dht_router("dht.aelitis.com", 6881)
    session.add_dht_router("dht.wifi.pps.tv", 6881)
    session.add_dht_router("dht1.anan.club", 6881)
    session.add_dht_router("dht2.anan.club", 6881)
    session.add_dht_router("dht.torren.to", 6881)
    session.add_dht_router("dht.waq001.com", 6881)
    session.add_dht_router("dht.nyaatorrents.info", 6881)
    session.add_dht_router("dht.kkcomics.com", 6881)
    session.add_dht_router("dht.3322.org", 6881)

    session.start_dht()
    session.start_lsd()
    session.start_upnp()
    session.start_natpmp()
    
    save_path = os.path.join(os.getcwd(), "downloads")
    os.makedirs(save_path, exist_ok=True)
    params = {'save_path': save_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}

    handle = None
    info = None

    try:
        if choice == "Torrent file":
            torrent_path = questionary.path("Enter the path to the .torrent file:").ask()
            if not torrent_path:
                console.print("[red]❌ No path entered. Exiting.[/red]")
                sys.exit(1)

            torrent_path = torrent_path.strip().strip('\'"')

            if os.path.isfile(torrent_path):
                pass
            elif os.path.isdir(torrent_path):
                console.print(f"[red]❌ Directory input not supported. Please enter the full path to a .torrent file.[/red]")
                sys.exit(1)
            else:
                console.print(f"[red]❌ Path does not exist: {torrent_path}[/red]")
                sys.exit(1)

            try:
                info = lt.torrent_info(torrent_path)
            except Exception as e:
                console.print(f"[red]❌ Failed to load torrent info: {e}[/red]")
                sys.exit(1)

            params['ti'] = info

            resume_data = load_resume_data(str(info.info_hash()))
            if resume_data:
                params['resume_data'] = resume_data

            handle = session.add_torrent(params)

            extra_trackers = [
                "udp://tracker.opentrackr.org:1337/announce",
                "udp://tracker.openbittorrent.com:80/announce",
                "udp://tracker.leechers-paradise.org:6969/announce",
                "udp://tracker.internetwarriors.net:1337/announce",
                "udp://exodus.desync.com:6969/announce",
                "udp://tracker.torrent.eu.org:451/announce",
                "udp://9.rarbg.to:2710/announce"
            ]

            for tracker_url in extra_trackers:
                try:
                    handle.add_tracker({'url': tracker_url})
                except Exception as e:
                    console.print(f"[red]⚠️ Failed to add tracker: {tracker_url} — {e}[/red]")
                    continue
                
            console.print(f"\n📁 Downloads will be saved to: [bold green]{os.path.join(save_path, info.name())}[/bold green]\n")
            console.print("[bold cyan]ℹ️  Press [yellow]Ctrl+C[/yellow] at any time to pause and save your download progress. You can resume it later.[/bold cyan]\n")
            metadata_announced = True

        else:
            magnet_link = questionary.text("Paste the magnet link:").ask()
            if not magnet_link:
                console.print("[red]❌ No magnet link entered. Exiting.[/red]")
                sys.exit(1)

            magnet_link = magnet_link.strip().strip('\'"')

            if not magnet_link.startswith("magnet:"):
                console.print("[red]❌ Invalid magnet link format.[/red]")
                sys.exit(1)

            handle = lt.add_magnet_uri(session, magnet_link, params)
            if handle is None:
                console.print("[red]❌ Failed to add magnet link. Handle is None.[/red]")
                sys.exit(1)

            console.print(f"\n⬇️ Downloads will be saved to: [bold green]{save_path}[/bold green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error adding torrent/magnet: {e}[/red]")
        sys.exit(1)

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )
    task_id = progress.add_task("[cyan]Downloading...", total=100)

    states = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']

    metadata_announced = False

    try:
        with Live(console=console, refresh_per_second=4) as live:
            while True:
                s = handle.status()
                progress.update(task_id, completed=s.progress * 100)

                state_str = states[s.state] if s.state < len(states) else "unknown"
                if state_str == 'downloading metadata':
                    activity = "[cyan]Fetching torrent metadata from peers...[/cyan]"
                elif state_str == 'checking':
                    activity = "[yellow]Checking existing files for integrity...[/yellow]"
                elif state_str == 'downloading':
                    activity = f"[green]Downloading data from {s.num_peers} peers...[/green]"
                elif state_str == 'seeding':
                    activity = f"[magenta]Seeding to {s.num_peers} peers[/magenta]"
                else:
                    activity = f"[white]{state_str.capitalize()}[/white]"

                if not info and handle.has_metadata():
                    info = handle.get_torrent_info()
                
                    if choice == "Magnet link" and not metadata_announced:
                        console.print(f"\n 📁 Metadata fetched. Downloads will be saved to: [bold green]{os.path.join(save_path, info.name())}[/bold green]\n")
                        metadata_announced = True
                    continue

                size_gb = (info.total_size() / (1024 ** 3)) if info else 0
                trackers_list = list(info.trackers()) if info else []

                name_text = f"[bold bright_cyan]{info.name() if info else 'Loading...'}[/bold bright_cyan]"

                stats_labels = (
                    "[bold yellow]Size:[/bold yellow]\n"
                    "[bold yellow]Pieces:[/bold yellow]\n"
                    "[bold yellow]Trackers:[/bold yellow]\n"
                    "[bold yellow]State:[/bold yellow]\n"
                    "[bold yellow]Peers:[/bold yellow]\n"
                    "[bold yellow]DL Rate:[/bold yellow]\n"
                    "[bold yellow]UL Rate:[/bold yellow]"
                )

                stats_values = (
                    f"[bold yellow]{format_bytes(s.total_done)}[/bold yellow] / [cyan]{format_bytes(info.total_size()) if info else 0}[/cyan]\n"
                    f"[cyan]{info.num_pieces() if info else '?'}[/cyan]\n"
                    f"[magenta]{len(trackers_list)}[/magenta]\n"
                    f"{activity}\n"
                    f"[green]{s.num_peers}[/green]\n"
                    f"[yellow]{s.download_rate / 1000:.1f} kB/s[/yellow]\n"
                    f"[yellow]{s.upload_rate / 1000:.1f} kB/s[/yellow]"
                )

                labels = Text.from_markup(stats_labels, justify="right")
                values = Text.from_markup(stats_values, justify="left")
                stats_columns = Columns([labels, values], padding=(0, 2), expand=False)

                info_panel = Panel(
                    Group(
                        Align.center(Text.from_markup(name_text)),
                        stats_columns,
                    ),
                    title="[bold magenta]Torrent Info & Stats[/bold magenta]",
                    border_style="bright_magenta",
                    padding=(1, 2),
                    width=60,
                )

                progress_panel = Panel(
                    progress.get_renderable(),
                    border_style="cyan",
                    padding=(0, 2),
                    title="[bold cyan]Download Progress[/bold cyan]",
                    width=60,
                )

                layout_group = Group(
                    Align.center(info_panel),
                    Align.center(progress_panel),
                )

                live.update(Align.center(layout_group, vertical="middle"))

                if s.is_seeding:
                    break

                time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]🔁 Stopping download and saving resume data...[/bold yellow]")
        if handle:
            save_resume_data(handle)
            console.print("[bold green]✅ Resume data saved.[/bold green]")
        sys.exit(0)

    save_resume_data(handle)
    console.print("[bold green]\n✅ Download completed![/bold green]\n")

if __name__ == "__main__":
    main()