"""Interactive command-line interface for the reconciliation data generator."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .models import GenerationConfig
from .scenarios import list_scenarios, get_scenario, SCENARIO_REGISTRY
from .generator import DataGenerator
from .writer import ExcelWriter


# Custom style for questionary prompts
CUSTOM_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'fg:white bold'),
    ('answer', 'fg:green bold'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:green'),
    ('separator', 'fg:gray'),
    ('instruction', 'fg:gray italic'),
    ('text', 'fg:white'),
    ('disabled', 'fg:gray italic'),
])

console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║          🔄 Reconciliation Test Data Generator 🔄              ║
║                                                               ║
║   Generate matched, potentially matched, and unmatched        ║
║   transaction datasets for reconciliation testing at scale    ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan")


def print_scenarios_table():
    """Print a table of available scenarios."""
    table = Table(title="Available Reconciliation Scenarios", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")
    table.add_column("Dataset 1", style="yellow")
    table.add_column("Dataset 2", style="yellow")
    
    for scenario in list_scenarios():
        table.add_row(
            scenario["name"],
            scenario["description"],
            scenario["dataset1_name"],
            scenario["dataset2_name"]
        )
    
    console.print(table)
    console.print()


def ask_scenario() -> str:
    """Ask user to select a reconciliation scenario."""
    scenarios = list_scenarios()
    choices = [
        questionary.Choice(
            title=f"{s['display_name']} - {s['description'][:50]}...",
            value=s['name']
        )
        for s in scenarios
    ]
    
    return questionary.select(
        "Which reconciliation scenario would you like to generate?",
        choices=choices,
        style=CUSTOM_STYLE,
        instruction="(Use arrow keys to navigate, Enter to select)"
    ).ask()


def ask_row_count() -> int:
    """Ask user for the number of rows to generate."""
    presets = [
        questionary.Choice(title="500 rows (quick test)", value=500),
        questionary.Choice(title="5,000 rows (quick test)", value=5000),
        questionary.Choice(title="10,000 rows (small test)", value=10000),
        questionary.Choice(title="50,000 rows (medium test)", value=50000),
        questionary.Choice(title="100,000 rows (large test)", value=100000),
        questionary.Choice(title="500,000 rows (stress test)", value=500000),
        questionary.Choice(title="1,000,000 rows (scale test)", value=1000000),
        questionary.Choice(title="Custom amount...", value=-1),
    ]
    
    result = questionary.select(
        "How many source records do you want to generate?",
        choices=presets,
        style=CUSTOM_STYLE,
        instruction="(Target rows will vary based on 1:N matches)"
    ).ask()
    
    if result == -1:
        custom = questionary.text(
            "Enter the number of rows:",
            validate=lambda x: x.isdigit() and int(x) > 0,
            style=CUSTOM_STYLE
        ).ask()
        return int(custom)
    
    return result


def ask_match_distribution() -> tuple[float, float]:
    """Ask user for match distribution percentages."""
    console.print("\n[bold cyan]Match Distribution Configuration[/bold cyan]")
    console.print("Configure how records should be distributed across match buckets.\n")
    
    CUSTOM = "CUSTOM"  # Sentinel value since questionary ignores None
    
    presets = [
        questionary.Choice(
            title="Balanced (60% matched, 25% potential, 15% unmatched)", 
            value=(0.60, 0.25)
        ),
        questionary.Choice(
            title="High Match (80% matched, 15% potential, 5% unmatched)", 
            value=(0.80, 0.15)
        ),
        questionary.Choice(
            title="Low Match (40% matched, 30% potential, 30% unmatched)", 
            value=(0.40, 0.30)
        ),
        questionary.Choice(
            title="Challenging (30% matched, 40% potential, 30% unmatched)", 
            value=(0.30, 0.40)
        ),
        questionary.Choice(
            title="Custom percentages...", 
            value=CUSTOM
        ),
    ]
    
    result = questionary.select(
        "Select a match distribution preset:",
        choices=presets,
        style=CUSTOM_STYLE
    ).ask()
    
    if result is None:
        return None, None
    
    if result == CUSTOM:
        # Custom input
        match_pct = questionary.text(
            "Exact match percentage (0-100):",
            default="60",
            validate=lambda x: x.replace('.', '').isdigit() and 0 <= float(x) <= 100,
            style=CUSTOM_STYLE
        ).ask()
        
        if match_pct is None:
            return None, None
        
        potential_pct = questionary.text(
            "Potential match percentage (0-100):",
            default="25",
            validate=lambda x: x.replace('.', '').isdigit() and 0 <= float(x) <= 100,
            style=CUSTOM_STYLE
        ).ask()
        
        if potential_pct is None:
            return None, None
        
        match_val = float(match_pct) / 100
        potential_val = float(potential_pct) / 100
        
        if match_val + potential_val > 1.0:
            console.print("[red]Error: Match + Potential cannot exceed 100%[/red]")
            return ask_match_distribution()
        
        return match_val, potential_val
    
    return result


def ask_one_to_n_config() -> tuple[float, int, int]:
    """Ask user for 1:N match configuration."""
    console.print("\n[bold cyan]1:N Potential Match Configuration[/bold cyan]")
    console.print("Configure how many potentially matched records should be 1:N aggregate groups.\n")
    
    CUSTOM = "CUSTOM"  # Sentinel value since questionary ignores None
    
    presets = [
        questionary.Choice(
            title="Low 1:N (20% of potential matches are 1:N, 2-3 splits)",
            value=(0.20, 2, 3)
        ),
        questionary.Choice(
            title="Medium 1:N (35% of potential matches are 1:N, 2-5 splits)",
            value=(0.35, 2, 5)
        ),
        questionary.Choice(
            title="High 1:N (50% of potential matches are 1:N, 2-7 splits)",
            value=(0.50, 2, 7)
        ),
        questionary.Choice(
            title="Custom configuration...", 
            value=CUSTOM
        ),
    ]
    
    result = questionary.select(
        "Select a 1:N match preset:",
        choices=presets,
        style=CUSTOM_STYLE
    ).ask()
    
    if result is None:
        return None, None, None
    
    if result == CUSTOM:
        ratio = questionary.text(
            "Percentage of potential matches that are 1:N (0-100):",
            default="30",
            validate=lambda x: x.replace('.', '').isdigit() and 0 <= float(x) <= 100,
            style=CUSTOM_STYLE
        ).ask()
        
        if ratio is None:
            return None, None, None
        
        min_splits = questionary.text(
            "Minimum number of target records per 1:N match:",
            default="2",
            validate=lambda x: x.isdigit() and int(x) >= 2,
            style=CUSTOM_STYLE
        ).ask()
        
        if min_splits is None:
            return None, None, None
        
        max_splits = questionary.text(
            "Maximum number of target records per 1:N match:",
            default="5",
            validate=lambda x: x.isdigit() and int(x) >= int(min_splits),
            style=CUSTOM_STYLE
        ).ask()
        
        if max_splits is None:
            return None, None, None
        
        return float(ratio) / 100, int(min_splits), int(max_splits)
    
    return result


def ask_variance_config() -> tuple[float, int]:
    """Ask user for potential match variance configuration."""
    console.print("\n[bold cyan]Potential Match Variance Configuration[/bold cyan]")
    console.print("Configure variance parameters for potential (near) matches.\n")
    
    CUSTOM = "CUSTOM"  # Sentinel value since questionary ignores None
    
    presets = [
        questionary.Choice(
            title="Zero tolerance (0% amount, 0 days)", 
            value=(0.0, 0)
        ),
        questionary.Choice(
            title="Tight tolerance (±2% amount, ±1 day)", 
            value=(0.02, 1)
        ),
        questionary.Choice(
            title="Normal tolerance (±5% amount, ±3 days)", 
            value=(0.05, 3)
        ),
        questionary.Choice(
            title="Loose tolerance (±10% amount, ±7 days)", 
            value=(0.10, 7)
        ),
        questionary.Choice(
            title="Custom tolerance...", 
            value=CUSTOM
        ),
    ]
    
    result = questionary.select(
        "Select a variance tolerance preset:",
        choices=presets,
        style=CUSTOM_STYLE
    ).ask()
    
    if result is None:
        return None, None
    
    if result == CUSTOM:
        amount_var = questionary.text(
            "Amount variance percentage (e.g., 5 for ±5%):",
            default="5",
            validate=lambda x: x.replace('.', '').isdigit() and 0 <= float(x) <= 50,
            style=CUSTOM_STYLE
        ).ask()
        
        if amount_var is None:
            return None, None
        
        date_var = questionary.text(
            "Date variance in days (e.g., 3 for ±3 days):",
            default="3",
            validate=lambda x: x.isdigit() and 0 <= int(x) <= 30,
            style=CUSTOM_STYLE
        ).ask()
        
        if date_var is None:
            return None, None
        
        return float(amount_var) / 100, int(date_var)
    
    return result


def ask_output_path(scenario_name: str) -> str:
    """Ask user for output subfolder path.

    Returns the path to a timestamped subfolder that will contain
    the XLSX and CSV files.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"recon_test_data_{scenario_name.replace('-', '_')}_{timestamp}"
    
    use_default = questionary.confirm(
        f"Save output to folder '{default_name}/'?",
        default=True,
        style=CUSTOM_STYLE
    ).ask()
    
    if use_default:
        return default_name
    
    custom_path = questionary.path(
        "Enter output folder path:",
        default=default_name,
        style=CUSTOM_STYLE
    ).ask()
    
    # Strip any .xlsx extension the user may have typed
    if custom_path.endswith('.xlsx'):
        custom_path = custom_path[:-5]
    
    return custom_path


def ask_num_mapping_keys() -> Optional[int]:
    """Ask user how many non-monetary mapping keys to declare per dataset."""
    console.print("\n[bold cyan]Mapping Key Configuration[/bold cyan]")
    console.print(
        "Choose how many non-monetary mapping keys each dataset declares. "
        "Monetary keys are always exactly 1.\n"
    )

    presets = [
        questionary.Choice(title="1 key  (single unique reference key)", value=1),
        questionary.Choice(title="2 keys (composite: reference + date) [default]", value=2),
        questionary.Choice(title="3 keys (composite + allocation key, complex)", value=3),
    ]

    return questionary.select(
        "How many mapping keys should each dataset declare?",
        choices=presets,
        default=presets[1],
        style=CUSTOM_STYLE,
    ).ask()


def ask_seed() -> Optional[int]:
    """Ask user for random seed (for reproducibility)."""
    use_seed = questionary.confirm(
        "Use a specific random seed for reproducibility?",
        default=False,
        style=CUSTOM_STYLE
    ).ask()
    
    if use_seed:
        seed = questionary.text(
            "Enter seed value:",
            default="42",
            validate=lambda x: x.isdigit(),
            style=CUSTOM_STYLE
        ).ask()
        return int(seed)
    
    return None


def confirm_configuration(config: GenerationConfig, scenario) -> bool:
    """Display configuration summary and ask for confirmation."""
    console.print("\n")
    
    # Show declared mapping keys for the configured num_mapping_keys.
    scenario.num_mapping_keys = config.num_mapping_keys
    dataset1_keys = scenario.active_mapping_keys1
    dataset2_keys = scenario.active_mapping_keys2
    dataset1_monetary = [col.name for col in scenario.dataset1_schema if col.is_monetary]
    dataset2_monetary = [col.name for col in scenario.dataset2_schema if col.is_monetary]
    
    # Create summary table
    table = Table(title="Generation Configuration Summary", show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Scenario", scenario.display_name)
    table.add_row("Source Rows", f"{config.total_source_rows:,}")
    table.add_row("Mapping Keys", f"{config.num_mapping_keys} per dataset")
    table.add_row("", "")
    table.add_row("[bold]Datasets[/bold]", "")
    table.add_row(f"  {scenario.dataset1_name}", f"Keys: {', '.join(dataset1_keys)}")
    table.add_row("", f"Amount: {', '.join(dataset1_monetary)}")
    table.add_row(f"  {scenario.dataset2_name}", f"Keys: {', '.join(dataset2_keys)}")
    table.add_row("", f"Amount: {', '.join(dataset2_monetary)}")
    table.add_row("", "")
    table.add_row("[bold]Match Distribution[/bold]", "")
    table.add_row("  Matched (Exact 1:1)", f"{config.match_percent * 100:.1f}%")
    table.add_row("  Potentially Matched", f"{config.potential_percent * 100:.1f}%")
    table.add_row("  Unmatched", f"{config.unmatched_percent * 100:.1f}%")
    table.add_row("", "")
    table.add_row("[bold]1:N Configuration[/bold]", "")
    table.add_row("  1:N Ratio (of potential)", f"{config.one_to_n_ratio * 100:.1f}%")
    table.add_row("  Splits Range", f"{config.min_n_splits} - {config.max_n_splits}")
    table.add_row("", "")
    table.add_row("[bold]Variance Settings[/bold]", "")
    table.add_row("  Amount Variance", f"±{config.amount_variance_percent * 100:.1f}%")
    table.add_row("  Date Variance", f"±{config.date_variance_days} days")
    table.add_row("", "")
    table.add_row("Output File", config.output_path)
    table.add_row("Random Seed", str(config.seed) if config.seed else "Random")
    
    console.print(table)
    console.print()
    
    return questionary.confirm(
        "Proceed with data generation?",
        default=True,
        style=CUSTOM_STYLE
    ).ask()


def run_generation(config: GenerationConfig):
    """Run the data generation process with progress display."""
    console.print("\n[bold green]Starting data generation...[/bold green]\n")
    
    # Initialize scenario and generator
    scenario = get_scenario(config.scenario)
    if config.seed:
        scenario = type(scenario)(seed=config.seed)
    
    generator = DataGenerator(scenario, config)
    writer = ExcelWriter(config.output_path, scenario)
    
    # Calculate expected chunks for progress bar
    expected_chunks = max(1, config.total_source_rows // config.chunk_size + 1)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Generating records...", total=expected_chunks)
            
            for source_chunk, target_chunk in generator.generate():
                writer.write_chunk(source_chunk, target_chunk)
                progress.advance(task)
            
            progress.update(task, description="Finalizing files...")
        
        # Finalize and save (XLSX + 2 CSVs)
        output_files = writer.finalize(generator.stats)
        writer.close()
        
        # Print success message with stats
        console.print("\n[bold green]✓ Data generation complete![/bold green]\n")
        
        stats_table = Table(title="Generation Statistics", show_header=False)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green", justify="right")
        
        for label, value in generator.stats.to_dict().items():
            stats_table.add_row(label, f"{value:,}")
        
        console.print(stats_table)
        console.print(f"\n[bold]Output folder:[/bold]  {output_files['dir']}")
        console.print(f"  [bold]XLSX:[/bold]  {output_files['xlsx']}")
        console.print(f"  [bold]CSV (source):[/bold]  {output_files['csv_source']}")
        console.print(f"  [bold]CSV (target):[/bold]  {output_files['csv_target']}")
        
    except Exception as e:
        console.print(f"\n[bold red]Error during generation:[/bold red] {e}")
        raise


def interactive_mode():
    """Run the interactive question-based CLI."""
    print_banner()
    
    # Show available scenarios
    print_scenarios_table()
    
    # Gather configuration through questions
    scenario = ask_scenario()
    if scenario is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    row_count = ask_row_count()
    if row_count is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    match_pct, potential_pct = ask_match_distribution()
    if match_pct is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    one_to_n_ratio, min_splits, max_splits = ask_one_to_n_config()
    if one_to_n_ratio is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    amount_var, date_var = ask_variance_config()
    if amount_var is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    num_mapping_keys = ask_num_mapping_keys()
    if num_mapping_keys is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    output_path = ask_output_path(scenario)
    if output_path is None:
        console.print("\n[yellow]Generation cancelled.[/yellow]")
        return
    
    seed = ask_seed()
    
    # Build configuration
    config = GenerationConfig(
        scenario=scenario,
        total_source_rows=row_count,
        match_percent=match_pct,
        potential_percent=potential_pct,
        one_to_n_ratio=one_to_n_ratio,
        min_n_splits=min_splits,
        max_n_splits=max_splits,
        amount_variance_percent=amount_var,
        date_variance_days=date_var,
        num_mapping_keys=num_mapping_keys,
        output_path=output_path,
        seed=seed,
    )
    
    # Validate
    errors = config.validate()
    if errors:
        console.print("\n[bold red]Configuration errors:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        return
    
    # Get scenario display name for confirmation
    scenario_obj = get_scenario(scenario)
    
    # Confirm and generate
    if confirm_configuration(config, scenario_obj):
        run_generation(config)
    else:
        console.print("\n[yellow]Generation cancelled.[/yellow]")


def quick_mode(
    scenario: str,
    rows: int,
    match_pct: float = 0.60,
    potential_pct: float = 0.25,
    num_mapping_keys: int = 2,
    output: Optional[str] = None,
    seed: Optional[int] = None
):
    """Run in quick mode with command-line arguments."""
    print_banner()
    
    if scenario not in SCENARIO_REGISTRY:
        console.print(f"[red]Unknown scenario: {scenario}[/red]")
        console.print(f"Available: {', '.join(SCENARIO_REGISTRY.keys())}")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output or f"recon_test_data_{scenario.replace('-', '_')}_{timestamp}"
    
    config = GenerationConfig(
        scenario=scenario,
        total_source_rows=rows,
        match_percent=match_pct / 100 if match_pct > 1 else match_pct,
        potential_percent=potential_pct / 100 if potential_pct > 1 else potential_pct,
        num_mapping_keys=num_mapping_keys,
        output_path=output_path,
        seed=seed,
    )
    
    errors = config.validate()
    if errors:
        console.print("\n[bold red]Configuration errors:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        return
    
    scenario_obj = get_scenario(scenario)
    if confirm_configuration(config, scenario_obj):
        run_generation(config)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate reconciliation test data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  recon-datagen                              # Interactive mode
  recon-datagen --quick -s bank-recon -n 10000
  recon-datagen --list                       # List scenarios
        """
    )
    
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick mode (skip interactive prompts)'
    )
    parser.add_argument(
        '--scenario', '-s',
        type=str,
        help='Scenario name (for quick mode)'
    )
    parser.add_argument(
        '--rows', '-n',
        type=int,
        help='Number of source rows (for quick mode)'
    )
    parser.add_argument(
        '--match-pct', '-m',
        type=float,
        default=60,
        help='Match percentage (default: 60)'
    )
    parser.add_argument(
        '--potential-pct', '-p',
        type=float,
        default=25,
        help='Potential match percentage (default: 25)'
    )
    parser.add_argument(
        '--num-keys', '-k',
        type=int,
        default=2,
        choices=[1, 2, 3],
        help='Number of non-monetary mapping keys per dataset, 1-3 (default: 2)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available scenarios'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print_banner()
        print_scenarios_table()
        return
    
    if args.quick:
        if not args.scenario or not args.rows:
            console.print("[red]Quick mode requires --scenario and --rows[/red]")
            parser.print_help()
            return
        quick_mode(
            scenario=args.scenario,
            rows=args.rows,
            match_pct=args.match_pct,
            potential_pct=args.potential_pct,
            num_mapping_keys=args.num_keys,
            output=args.output,
            seed=args.seed
        )
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
